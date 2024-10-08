from langchain_core.embeddings import Embeddings
from langchain_core.tools import StructuredTool
from langchain_core.vectorstores import VectorStoreRetriever

from redbox.chains.components import (
    get_all_chunks_retriever,
    get_embeddings,
    get_metadata_retriever,
    get_parameterised_retriever,
)
from redbox.graph.nodes.tools import build_search_documents_tool
from redbox.graph.root import get_root_graph
from redbox.models.chain import RedboxState
from redbox.models.chat import ChatRoute
from redbox.models.file import ChunkResolution
from redbox.models.graph import (
    FINAL_RESPONSE_TAG,
    ROUTABLE_KEYWORDS,
    ROUTE_NAME_TAG,
    SOURCE_DOCUMENTS_TAG,
    RedboxEventType,
)
from redbox.models.settings import Settings
from redbox.transform import flatten_document_state


async def _default_callback(*args, **kwargs):
    return None


class Redbox:
    def __init__(
        self,
        all_chunks_retriever: VectorStoreRetriever | None = None,
        parameterised_retriever: VectorStoreRetriever | None = None,
        metadata_retriever: VectorStoreRetriever | None = None,
        embedding_model: Embeddings | None = None,
        env: Settings | None = None,
        debug: bool = False,
    ):
        _env = env or Settings()

        # Retrievers

        _all_chunks_retriever = all_chunks_retriever or get_all_chunks_retriever(_env)
        _parameterised_retriever = parameterised_retriever or get_parameterised_retriever(_env)
        _metadata_retriever = metadata_retriever or get_metadata_retriever(_env)
        _embedding_model = embedding_model or get_embeddings(_env)

        # Tools

        search_documents = build_search_documents_tool(
            es_client=_env.elasticsearch_client(),
            index_name=f"{_env.elastic_root_index}-chunk",
            embedding_model=_embedding_model,
            embedding_field_name=_env.embedding_document_field_name,
            chunk_resolution=ChunkResolution.normal,
        )

        tools: dict[str, StructuredTool] = {
            "_search_documents": search_documents,
        }

        self.graph = get_root_graph(
            all_chunks_retriever=_all_chunks_retriever,
            parameterised_retriever=_parameterised_retriever,
            metadata_retriever=_metadata_retriever,
            tools=tools,
            debug=debug,
        )

    async def run(
        self,
        input: RedboxState,
        response_tokens_callback=_default_callback,
        route_name_callback=_default_callback,
        documents_callback=_default_callback,
        metadata_tokens_callback=_default_callback,
        activity_event_callback=_default_callback,
    ) -> RedboxState:
        final_state = None
        async for event in self.graph.astream_events(input=input, version="v2", config={"recursion_limit": 50}):
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
            elif kind == "on_retriever_end" and SOURCE_DOCUMENTS_TAG in tags:
                await documents_callback(event["data"]["output"])
            elif kind == "on_tool_end" and SOURCE_DOCUMENTS_TAG in tags:
                documents = flatten_document_state(event["data"]["output"].get("documents", {}))
                await documents_callback(documents)
            elif kind == "on_custom_event" and event["name"] == RedboxEventType.on_source_report.value:
                await documents_callback(event["data"])
            elif kind == "on_custom_event" and event["name"] == RedboxEventType.on_metadata_generation.value:
                await metadata_tokens_callback(event["data"])
            elif kind == "on_custom_event" and event["name"] == RedboxEventType.activity.value:
                await activity_event_callback(event["data"])
            elif kind == "on_chain_end" and event["name"] == "LangGraph":
                final_state = RedboxState(**event["data"]["output"])
        return final_state

    def get_available_keywords(self) -> dict[ChatRoute, str]:
        return ROUTABLE_KEYWORDS

    def draw(self, output_path="RedboxAIArchitecture.png"):
        from langchain_core.runnables.graph import MermaidDrawMethod

        self.graph(xray=True).draw_mermaid_png(draw_method=MermaidDrawMethod.API, output_file_path=output_path)
