from urllib.parse import urlparse
from uuid import uuid4

import pytest
from elasticsearch import Elasticsearch
from langchain_core.embeddings.fake import FakeEmbeddings
from langchain_core.messages import AIMessage
from langgraph.prebuilt import ToolNode

from redbox.graph.nodes.tools import (
    build_govuk_search_tool,
    build_search_documents_tool,
    build_search_wikipedia_tool,
)
from redbox.models.chain import AISettings, RedboxQuery, RedboxState
from redbox.models.file import ChunkCreatorType, ChunkMetadata, ChunkResolution
from redbox.models.settings import Settings
from redbox.test.data import RedboxChatTestCase
from redbox.transform import flatten_document_state
from tests.retriever.test_retriever import TEST_CHAIN_PARAMETERS


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

    tool_node = ToolNode(tools=[search])
    result_state = tool_node.invoke(
        RedboxState(
            request=stored_file_parameterised.query,
            messages=[
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "_search_documents",
                            "args": {"query": stored_file_parameterised.query.question},
                            "id": "1",
                        }
                    ],
                )
            ],
        )
    )

    if not permission:
        # No new messages update emitted
        assert result_state["messages"][0].content == ""
        assert result_state["messages"][0].artifact == []
    else:
        result_flat = result_state["messages"][0].artifact

        # Check state update is formed as expected
        assert isinstance(result_state, dict)
        assert len(result_state) == 1

        # Check flattened documents match expected, similar to retriever
        assert len(result_flat) == chain_params["rag_k"]
        assert {c.page_content for c in result_flat} <= {c.page_content for c in permitted_docs}
        assert {c.metadata["uri"] for c in result_flat} <= set(stored_file_parameterised.query.permitted_s3_keys)

        if selected:
            assert {c.page_content for c in result_flat} <= {c.page_content for c in selected_docs}
            assert {c.metadata["uri"] for c in result_flat} <= set(stored_file_parameterised.query.s3_keys)


@pytest.mark.xfail(reason="calls openai")
def test_govuk_search_tool():
    tool = build_govuk_search_tool()

    tool_node = ToolNode(tools=[tool])
    response = tool_node.invoke(
        {
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "_search_govuk",
                            "args": {"query": "Cuba Travel Advice"},
                            "id": "1",
                        }
                    ],
                )
            ]
        }
    )
    assert response["messages"][0].content != ""

    # assert at least one document is travel advice
    assert any(
        "/foreign-travel-advice/cuba" in document.metadata["uri"] for document in response["messages"][0].artifact
    )

    for document in response["messages"][0].artifact:
        assert document.page_content != ""
        metadata = ChunkMetadata.model_validate(document.metadata)
        assert urlparse(metadata.uri).hostname == "www.gov.uk"
        assert metadata.creator_type == ChunkCreatorType.gov_uk


def test_wikipedia_tool():
    tool = build_search_wikipedia_tool()
    tool_node = ToolNode(tools=[tool])
    response = tool_node.invoke(
        {
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "_search_wikipedia",
                            "args": {"query": "What was the highest office held by Gordon Brown"},
                            "id": "1",
                        }
                    ],
                )
            ]
        }
    )
    assert response["messages"][0].content != ""

    for document in response["messages"][0].artifact:
        assert document.page_content != ""
        metadata = ChunkMetadata.model_validate(document.metadata)
        assert urlparse(metadata.uri).hostname == "en.wikipedia.org"
        assert metadata.creator_type == ChunkCreatorType.wikipedia


@pytest.mark.parametrize(
    "is_filter, relevant_return, query, keyword",
    [
        (False, False, "UK government use of AI", "artificial intelligence"),
        (True, True, "UK government use of AI", "artificial intelligence"),
    ],
)
@pytest.mark.vcr
@pytest.mark.xfail(reason="calls openai")
def test_gov_filter_AI(is_filter, relevant_return, query, keyword):
    def run_tool(is_filter):
        tool = build_govuk_search_tool(filter=is_filter)
        state_update = tool.invoke(
            {
                "query": query,
                "state": RedboxState(
                    request=RedboxQuery(
                        question=query,
                        s3_keys=[],
                        user_uuid=uuid4(),
                        chat_history=[],
                        ai_settings=AISettings(),
                        permitted_s3_keys=[],
                    )
                ),
            }
        )

        return flatten_document_state(state_update["documents"])

    # call gov tool without additional filter
    documents = run_tool(is_filter)
    assert any(keyword in document.page_content for document in documents) == relevant_return


@pytest.mark.vcr
@pytest.mark.xfail(reason="calls openai")
def test_gov_tool_params():
    query = "driving in the UK"
    tool = build_govuk_search_tool(filter=True)
    ai_setting = AISettings()

    tool_node = ToolNode(tools=[tool])
    response = tool_node.invoke(
        {
            "request": RedboxQuery(
                question=query,
                s3_keys=[],
                user_uuid=uuid4(),
                chat_history=[],
                ai_settings=ai_setting,
                permitted_s3_keys=[],
            ),
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "_search_govuk",
                            "args": {"query": query},
                            "id": "1",
                        }
                    ],
                )
            ],
        }
    )

    documents = response["messages"][-1].artifact

    # call gov tool without additional filter
    assert len(documents) == ai_setting.tool_govuk_returned_results
