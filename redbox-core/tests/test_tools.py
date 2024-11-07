from typing import Annotated, Any
from urllib.parse import urlparse
from uuid import UUID, uuid4

import pytest
from elasticsearch import Elasticsearch
from langchain_core.embeddings.fake import FakeEmbeddings
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

from redbox.graph.nodes.tools import (
    build_govuk_search_tool,
    build_search_documents_tool,
    build_search_wikipedia_tool,
    has_injected_state,
    is_valid_tool,
)
from redbox.models.settings import Settings
from redbox.models.chain import AISettings, RedboxQuery, RedboxState
from redbox.models.file import ChunkCreatorType, ChunkMetadata, ChunkResolution
from redbox.test.data import RedboxChatTestCase
from redbox.transform import flatten_document_state
from tests.retriever.test_retriever import TEST_CHAIN_PARAMETERS


def test_is_valid_tool():
    @tool
    def tool_with_type_hinting() -> dict[str, Any]:
        """Tool that returns a dictionary update."""
        return {"key": "value"}

    @tool
    def tool_without_type_hinting():
        """Tool that returns a dictionary update."""
        return {"key": "value"}

    assert is_valid_tool(tool_with_type_hinting)
    assert not is_valid_tool(tool_without_type_hinting)


def test_has_injected_state():
    @tool
    def tool_with_injected_state(query: str, state: Annotated[dict, InjectedState]) -> dict[str, Any]:
        """Tool that returns a dictionary update."""
        return {"key": "value"}

    @tool
    def tool_without_injected_state(query: str) -> dict[str, Any]:
        """Tool that returns a dictionary update."""
        return {"key": "value"}

    assert has_injected_state(tool_with_injected_state)
    assert not has_injected_state(tool_without_injected_state)


@pytest.mark.parametrize("chain_params", TEST_CHAIN_PARAMETERS)
def test_search_documents_tool(
    chain_params: dict,
    stored_file_parameterised: RedboxChatTestCase,
    es_client: Elasticsearch,
    es_index: str,
    embedding_model: FakeEmbeddings,
    env: Settings,
):
    """
    Tests the search documents tool.

    As this is a slight reworking of the parameterised retriever to
    work more as a tool, we partly just adapt the same unit test.

    Part of the rework is to emit a state, so some of our tests echo
    the structure_documents_* unit tests, which turn document
    lists into a DocumentState.

    Asserts:

    * If documents are selected and there's permission to get them
        * The length of the result is equal to the rag_k parameter
        * The result page content is a subset of all possible correct
        page content
        * The result contains only file_names the user selected
        * The result contains only file_names from permitted S3 keys
    * If documents are selected and there's no permission to get them
        * The length of the result is zero
    * If documents aren't selected and there's permission to get them
        * The length of the result is equal to the rag_k parameter
        * The result page content is a subset of all possible correct
        page content
        * The result contains only file_names from permitted S3 keys
    * If documents aren't selected and there's no permission to get them
        * The length of the result is zero

    And that:

    * The result is an appropriate update to RedboxState
    * The DocumentState is the right shape
    """
    for k, v in chain_params.items():
        setattr(stored_file_parameterised.query.ai_settings, k, v)

    selected_docs = stored_file_parameterised.get_docs_matching_query()
    permitted_docs = stored_file_parameterised.get_all_permitted_docs()

    selected = bool(stored_file_parameterised.query.s3_keys)
    permission = bool(stored_file_parameterised.query.permitted_s3_keys)

    # Build and run
    search = build_search_documents_tool(
        es_client=es_client,
        index_name=es_index,
        embedding_model=embedding_model,
        embedding_field_name=env.embedding_document_field_name,
        chunk_resolution=ChunkResolution.normal,
    )

    result_state = search.invoke(
        {
            "query": stored_file_parameterised.query.question,
            "state": RedboxState(
                request=stored_file_parameterised.query,
                text=stored_file_parameterised.query.question,
            ),
        }
    )

    if not permission:
        # No state update emitted
        assert result_state is None
    else:
        result_docstate = result_state["documents"]
        result_flat = flatten_document_state(result_state["documents"])

        # Check state update is formed as expected
        assert isinstance(result_state, dict)
        assert len(result_state) == 1
        assert "documents" in result_state

        # Check flattened documents match expected, similar to retriever
        assert len(result_flat) == chain_params["rag_k"]
        assert {c.page_content for c in result_flat} <= {c.page_content for c in permitted_docs}
        assert {c.metadata["uri"] for c in result_flat} <= set(stored_file_parameterised.query.permitted_s3_keys)

        if selected:
            assert {c.page_content for c in result_flat} <= {c.page_content for c in selected_docs}
            assert {c.metadata["uri"] for c in result_flat} <= set(stored_file_parameterised.query.s3_keys)

        # Check docstate is formed as expected, similar to transform tests
        for group_uuid, group_docs in result_docstate.items():
            assert isinstance(group_uuid, UUID)
            assert isinstance(group_docs, dict)

            for doc in group_docs.values():
                assert doc.metadata["uuid"] in group_docs
                assert group_docs[doc.metadata["uuid"]] == doc


def test_govuk_search_tool():
    tool = build_govuk_search_tool()

    state_update = tool.invoke(
        {
            "query": "Cuba Travel Advice",
            "state": RedboxState(
                request=RedboxQuery(
                    question="Search gov.uk for travel advice to cuba",
                    s3_keys=[],
                    user_uuid=uuid4(),
                    chat_history=[],
                    ai_settings=AISettings(),
                    permitted_s3_keys=[],
                )
            ),
        }
    )

    documents = flatten_document_state(state_update["documents"])

    # assert at least one document is travel advice
    assert any("/foreign-travel-advice/cuba" in document.metadata["uri"] for document in documents)

    for document in documents:
        assert document.page_content != ""
        metadata = ChunkMetadata.model_validate(document.metadata)
        assert urlparse(metadata.uri).hostname == "www.gov.uk"
        assert metadata.creator_type == ChunkCreatorType.gov_uk


def test_wikipedia_tool():
    tool = build_search_wikipedia_tool()
    state_update = tool.invoke(
        {
            "query": "Gordon Brown",
            "state": RedboxState(
                request=RedboxQuery(
                    question="What was the highest office held by Gordon Brown",
                    s3_keys=[],
                    user_uuid=uuid4(),
                    chat_history=[],
                    ai_settings=AISettings(),
                    permitted_s3_keys=[],
                )
            ),
        }
    )

    for document in flatten_document_state(state_update["documents"]):
        assert document.page_content != ""
        metadata = ChunkMetadata.model_validate(document.metadata)
        assert urlparse(metadata.uri).hostname == "en.wikipedia.org"
        assert metadata.creator_type == ChunkCreatorType.wikipedia
