from langchain_core.vectorstores import VectorStoreRetriever

from redbox.graph.root import get_root_graph
from redbox.models.chain import RedboxState
from redbox.models.chat import ChatRoute
from redbox.models.settings import Settings
from redbox.chains.components import get_all_chunks_retriever, get_metadata_retriever, get_parameterised_retriever
from redbox.graph.root import (
    ROUTABLE_KEYWORDS,
    ROUTE_NAME_TAG,
    FINAL_RESPONSE_TAG,
    SOURCE_DOCUMENTS_TAG,
)


async def _default_callback(*args, **kwargs):
    return None


class Redbox:
    def __init__(
        self,
        all_chunks_retriever: VectorStoreRetriever | None = None,
        parameterised_retriever: VectorStoreRetriever | None = None,
        metadata_retriever: VectorStoreRetriever | None = None,
        env: Settings | None = None,
        debug: bool = False,
        interrupt_after: list[str] = [],
    ):
        _env = env or Settings()
        _all_chunks_retriever = all_chunks_retriever or get_all_chunks_retriever(_env)
        _parameterised_retriever = parameterised_retriever or get_parameterised_retriever(_env)
        _metadata_retriever = metadata_retriever or get_metadata_retriever(_env)

        self.graph = get_root_graph(_all_chunks_retriever, _parameterised_retriever, _metadata_retriever, debug)

    async def run(
        self,
        input: RedboxState,
        response_tokens_callback=_default_callback,
        route_name_callback=_default_callback,
        documents_callback=_default_callback,
        metadata_tokens_callback=_default_callback,
    ) -> RedboxState:
        final_state = None
        async for event in self.graph.astream_events(input, version="v2"):
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
            elif kind == "on_chain_end" and ROUTE_NAME_TAG in tags:
                await route_name_callback(event["data"]["output"])
            elif kind == "on_retriever_end" and SOURCE_DOCUMENTS_TAG in tags:
                await documents_callback(event["data"]["output"])
            elif kind == "on_custom_event" and event["name"] == "on_metadata_generation":
                await metadata_tokens_callback(event["data"])
            elif kind == "on_chain_end" and event["name"] == "LangGraph":
                final_state = RedboxState(**event["data"]["output"])
        return final_state

    def get_available_keywords(self) -> dict[ChatRoute, str]:
        return ROUTABLE_KEYWORDS

    def draw(self, output_path="RedboxAIArchitecture.png"):
        from langchain_core.runnables.graph import MermaidDrawMethod

        self.graph(xray=True).draw_mermaid_png(draw_method=MermaidDrawMethod.API, output_file_path=output_path)
