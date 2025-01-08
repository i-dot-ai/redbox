from logging import getLogger
from typing import Literal

from langchain_core.vectorstores import VectorStoreRetriever

from redbox.graph.root import (
    get_chat_with_documents_graph,
    get_root_graph,
)
from redbox.models.chain import RedboxState
from redbox.models.graph import (
    FINAL_RESPONSE_TAG,
    ROUTE_NAME_TAG,
    SOURCE_DOCUMENTS_TAG,
    RedboxEventType,
)
from redbox.transform import flatten_document_state


async def _default_callback(*args, **kwargs):
    return None


logger = getLogger(__name__)


class Redbox:
    def __init__(
        self,
        retriever: VectorStoreRetriever,
        debug: bool = False,
    ):
        # Retrievers

        self.retriever = retriever

        self.graph = get_root_graph(
            retriever=self.retriever,
            debug=debug,
        )

    def run_sync(self, input: RedboxState):
        """
        Run Redbox without streaming events. This simpler, synchronous execution enables use of the graph debug logging
        """
        return self.graph.invoke(input=input)

    async def run(
        self,
        input: RedboxState,
        response_tokens_callback=_default_callback,
        route_name_callback=_default_callback,
        metadata_tokens_callback=_default_callback,
    ) -> RedboxState:
        final_state = None
        request_dict = input.request.model_dump()
        logger.info("Request: %s", {k: request_dict[k] for k in request_dict.keys() - {"ai_settings"}})
        async for event in self.graph.astream_events(
            input=input,
            version="v2",
            config={"recursion_limit": input.request.ai_settings.recursion_limit},
        ):
            kind = event["event"]
            tags = event.get("tags", [])
            if kind == "on_chat_model_stream" and FINAL_RESPONSE_TAG in tags:
                content = event["data"]["chunk"].content
                if isinstance(content, str):
                    await response_tokens_callback(content)
            elif kind == "on_chain_end" and FINAL_RESPONSE_TAG in tags:
                content = event["data"]["output"]
                if isinstance(content, str):
                    await response_tokens_callback(content)
            elif kind == "on_custom_event" and event["name"] == RedboxEventType.response_tokens.value:
                await response_tokens_callback(event["data"])
            elif kind == "on_chain_end" and ROUTE_NAME_TAG in tags:
                await route_name_callback(event["data"]["output"]["route_name"])
            elif kind == "on_custom_event" and event["name"] == RedboxEventType.on_metadata_generation.value:
                await metadata_tokens_callback(event["data"])
            elif kind == "on_chain_end" and event["name"] == "LangGraph":
                final_state = RedboxState(**event["data"]["output"])
        return final_state

    def draw(self, output_path=None, graph_to_draw: Literal["root", "chat_with_documents"] = "root"):
        from langchain_core.runnables.graph import MermaidDrawMethod

        if graph_to_draw == "root":
            graph = self.graph.get_graph()
        elif graph_to_draw == "chat/documents":
            graph = get_chat_with_documents_graph(self.retriever).get_graph()
        else:
            raise Exception("Invalid graph_to_draw")

        return graph.draw_mermaid_png(draw_method=MermaidDrawMethod.API, output_file_path=output_path)
