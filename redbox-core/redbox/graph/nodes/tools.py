from typing import Annotated, Any, get_args, get_origin, get_type_hints

from elasticsearch import Elasticsearch
from langchain_core.embeddings.embeddings import Embeddings
from langchain_core.tools import StructuredTool, Tool, tool
from langgraph.prebuilt import InjectedState

from redbox.models.file import ChunkResolution
from redbox.retriever.queries import add_document_filter_scores_to_query, build_document_query
from redbox.retriever.retrievers import query_to_documents
from redbox.transform import merge_documents, sort_documents, structure_documents_by_group_and_indices


def is_valid_tool(tool: StructuredTool) -> bool:
    """Checks whether the supplied tool will correctly update the state.

    In Redbox, tools must return a valid state update. Here we enforce they're
    at least typed to return a dictionary.
    """
    return_type = get_type_hints(tool.func).get("return", None)

    if isinstance(return_type, type):
        return issubclass(return_type, dict)

    # Check for dict with generics (e.g., dict[str, list])
    if hasattr(return_type, "__origin__") and return_type.__origin__ is dict:
        key_type, value_type = return_type.__args__
        if issubclass(key_type, str) and issubclass(value_type, Any):
            return True

    return False


def has_injected_state(tool: StructuredTool) -> bool:
    """Detects whether the tool has an argument typed with InjectedState.

    Adapted from functions in langgraph.prebuilt.tool_node
    """

    def _is_injection(type_arg: Any, injection_type: type[InjectedState]) -> bool:
        """Recursively checks for injection types."""
        if isinstance(type_arg, injection_type) or (
            isinstance(type_arg, type) and issubclass(type_arg, injection_type)
        ):
            return True
        origin_ = get_origin(type_arg)
        if origin_ is Annotated:
            return any(_is_injection(ta, injection_type) for ta in get_args(type_arg))
        return False

    full_schema = tool.get_input_schema()

    for type_ in full_schema.__annotations__.values():
        if _is_injection(type_, InjectedState):
            return True

    return False


def build_search_documents_tool(
    es_client: Elasticsearch,
    index_name: str,
    embedding_model: Embeddings,
    embedding_field_name: str,
    chunk_resolution: ChunkResolution | None,
) -> Tool:
    """Constructs a tool that searches the index and sets state["documents"]."""

    @tool
    def _search_documents(query: str, state: Annotated[dict, InjectedState]) -> dict[str, Any]:
        """
        Search for documents uploaded by the user based on a query string.

        This function performs a search over the user's uploaded documents
        and returns snippets from the documents ordered by relevance and
        grouped by document.

        Args:
            query (str): The search query string used to match documents.
                This could be a keyword, phrase, question, or text from
                the documents.

        Returns:
            dict[str, Any]: A collection of document objects that match the query.
        """
        query_vector = embedding_model.embed_query(query)
        selected_files = state["request"].s3_keys
        permitted_files = state["request"].permitted_s3_keys
        ai_settings = state["request"].ai_settings

        # Initial pass
        initial_query = build_document_query(
            query=query,
            query_vector=query_vector,
            selected_files=selected_files,
            permitted_files=permitted_files,
            embedding_field_name=embedding_field_name,
            chunk_resolution=chunk_resolution,
            ai_settings=ai_settings,
        )
        initial_documents = query_to_documents(es_client=es_client, index_name=index_name, query=initial_query)

        # Handle nothing found (as when no files are permitted)
        if not initial_documents:
            return None

        # Adjacent documents
        with_adjacent_query = add_document_filter_scores_to_query(
            elasticsearch_query=initial_query,
            ai_settings=ai_settings,
            centres=initial_documents,
        )
        adjacent_boosted = query_to_documents(es_client=es_client, index_name=index_name, query=with_adjacent_query)

        # Merge and sort
        merged_documents = merge_documents(initial=initial_documents, adjacent=adjacent_boosted)
        sorted_documents = sort_documents(documents=merged_documents)

        # Return as state update
        return {"documents": structure_documents_by_group_and_indices(sorted_documents)}

    return _search_documents
