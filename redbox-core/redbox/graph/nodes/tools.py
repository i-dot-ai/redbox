from typing import Annotated, Any, Iterable, get_args, get_origin, get_type_hints

import requests
import tiktoken
from elasticsearch import Elasticsearch
from langchain_community.utilities import WikipediaAPIWrapper
from langchain_core.documents import Document
from langchain_core.embeddings.embeddings import Embeddings
from langchain_core.messages import ToolCall
from langchain_core.tools import StructuredTool, Tool, tool
from langgraph.prebuilt import InjectedState

from redbox.models.chain import RedboxState
from redbox.models.file import ChunkCreatorType, ChunkMetadata, ChunkResolution
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
    """Constructs a tool that searches the index and sets state.documents."""

    @tool
    def _search_documents(query: str, state: Annotated[RedboxState, InjectedState]) -> dict[str, Any]:
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
        selected_files = state.request.s3_keys
        permitted_files = state.request.permitted_s3_keys
        ai_settings = state.request.ai_settings

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


def build_govuk_search_tool(num_results: int = 1) -> Tool:
    """Constructs a tool that searches gov.uk and sets state["documents"]."""

    tokeniser = tiktoken.encoding_for_model("gpt-4o")

    @tool
    def _search_govuk(query: str, state: Annotated[RedboxState, InjectedState]) -> dict[str, Any]:
        """
        Search for documents on gov.uk based on a query string.
        This endpoint is used to search for documents on gov.uk. There are many types of documents on gov.uk.
        Types include:
        - guidance
        - policy
        - legislation
        - news
        - travel advice
        - departmental reports
        - statistics
        - consultations
        - appeals
        """

        url_base = "https://www.gov.uk"
        required_fields = [
            "format",
            "title",
            "description",
            "indexable_content",
            "link",
        ]

        response = requests.get(
            f"{url_base}/api/search.json",
            params={
                "q": query,
                "count": num_results,
                "fields": required_fields,
            },
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        response = response.json()

        mapped_documents = []
        for i, doc in enumerate(response["results"]):
            if any(field not in doc for field in required_fields):
                continue

            mapped_documents.append(
                Document(
                    page_content=doc["indexable_content"],
                    metadata=ChunkMetadata(
                        index=i,
                        uri=f"{url_base}{doc['link']}",
                        token_count=len(tokeniser.encode(doc["indexable_content"])),
                        creator_type=ChunkCreatorType.gov_uk,
                    ).model_dump(),
                )
            )

        return {"documents": structure_documents_by_group_and_indices(mapped_documents)}

    return _search_govuk


def build_search_wikipedia_tool(number_wikipedia_results=1, max_chars_per_wiki_page=12000) -> Tool:
    """Constructs a tool that searches Wikipedia"""
    _wikipedia_wrapper = WikipediaAPIWrapper(
        top_k_results=number_wikipedia_results,
        doc_content_chars_max=max_chars_per_wiki_page,
    )
    tokeniser = tiktoken.encoding_for_model("gpt-4o")

    @tool
    def _search_wikipedia(query: str, state: Annotated[RedboxState, InjectedState]) -> dict[str, Any]:
        """
        Search Wikipedia for information about the queried entity.
        Useful for when you need to answer general questions about people, places, objects, companies, facts, historical events, or other subjects.
        Input should be a search query.

        Args:
            query (str): The search query string used to find pages.
                This could be a keyword, phrase, or name

        Returns:
            response (str): The content of the relevant Wikipedia page
        """
        response = _wikipedia_wrapper.load(query)
        mapped_documents = [
            Document(
                page_content=doc.page_content,
                metadata=ChunkMetadata(
                    index=i,
                    uri=doc.metadata["source"],
                    token_count=len(tokeniser.encode(doc.page_content)),
                    creator_type=ChunkCreatorType.wikipedia,
                ).model_dump(),
            )
            for i, doc in enumerate(response)
        ]
        return {"documents": structure_documents_by_group_and_indices(mapped_documents)}

    return _search_wikipedia


class BaseRetrievalToolLogFormatter:
    def __init__(self, t: ToolCall) -> None:
        self.tool_call = t

    def log_call(self, tool_call: ToolCall):
        return f"Used {tool_call["name"]} to get more information"

    def log_result(self, documents: Iterable[Document]):
        if len(documents) == 0:
            return f"{self.tool_call["name"]} returned no documents"
        return f"Reading {documents[1].get("creator_type")} document{"s" if len(documents)>1 else ""} {','.join(set([d.metadata["uri"].split("/")[-1] for d in documents]))}"


class SearchWikipediaLogFormatter(BaseRetrievalToolLogFormatter):
    def log_call(self):
        return f"Searching Wikipedia for '{self.tool_call["args"]["query"]}'"

    def log_result(self, documents: Iterable[Document]):
        return f"Reading Wikipedia page{"s" if len(documents)>1 else ""} {','.join(set([d.metadata["uri"].split("/")[-1] for d in documents]))}"


class SearchDocumentsLogFormatter(BaseRetrievalToolLogFormatter):
    def log_call(self):
        return f"Searching your documents for '{self.tool_call["args"]["query"]}'"

    def log_result(self, documents: Iterable[Document]):
        return f"Reading {len(documents)} snippets from your documents {','.join(set([d.metadata.get("name", "") for d in documents]))}"


class SearchGovUKLogFormatter(BaseRetrievalToolLogFormatter):
    def log_call(self):
        return f"Searching .gov.uk pages for '{self.tool_call["args"]["query"]}'"

    def log_result(self, documents: Iterable[Document]):
        return f"Reading pages from .gov.uk, {','.join(set([d.metadata["uri"].split("/")[-1] for d in documents]))}"


__RETRIEVEAL_TOOL_MESSAGE_FORMATTERS = {
    "_search_wikipedia": SearchWikipediaLogFormatter,
    "_search_documents": SearchDocumentsLogFormatter,
    "_search_govuk": SearchGovUKLogFormatter,
}


def get_log_formatter_for_retrieval_tool(t: ToolCall) -> BaseRetrievalToolLogFormatter:
    return __RETRIEVEAL_TOOL_MESSAGE_FORMATTERS.get(t["name"], BaseRetrievalToolLogFormatter)(t)
