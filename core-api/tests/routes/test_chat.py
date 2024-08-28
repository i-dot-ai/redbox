import json
from typing import TYPE_CHECKING, Generator
from uuid import uuid4

import pytest
from _pytest.fixtures import FixtureRequest
from fastapi.testclient import TestClient
from jose import jwt
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_elasticsearch import ElasticsearchStore
from pytest_mock import MockerFixture
from redbox.models.chain import RedboxQuery
from redbox.models.chat import ChatResponse, ChatRoute
from redbox.test.data import RedboxChatTestCase, RedboxTestData, generate_test_cases
from starlette.websockets import WebSocketDisconnect

if TYPE_CHECKING:
    pass

EXPECTED_AVAILABLE_ROUTES = {"search"}

TEST_CASES = [
    test_case
    for generated_cases in [
        generate_test_cases(
            query=RedboxQuery(question="What is AI?", file_uuids=[], user_uuid=uuid4(), chat_history=[]),
            test_data=[
                RedboxTestData(0, 0, expected_llm_response=["Testing Response 1"], expected_route=ChatRoute.chat),
                RedboxTestData(1, 100, expected_llm_response=["Testing Response 1"], expected_route=ChatRoute.chat),
                RedboxTestData(10, 1200, expected_llm_response=["Testing Response 1"], expected_route=ChatRoute.chat),
            ],
            test_id="Basic Chat",
        ),
        generate_test_cases(
            query=RedboxQuery(question="What is AI?", file_uuids=[uuid4()], user_uuid=uuid4(), chat_history=[]),
            test_data=[
                RedboxTestData(
                    1, 1000, expected_llm_response=["Testing Response 1"], expected_route=ChatRoute.chat_with_docs
                ),
                RedboxTestData(
                    1, 50_000, expected_llm_response=["Testing Response 1"], expected_route=ChatRoute.chat_with_docs
                ),
                RedboxTestData(
                    1, 80_000, expected_llm_response=["Testing Response 1"], expected_route=ChatRoute.chat_with_docs
                ),
            ],
            test_id="Chat with single doc",
        ),
        generate_test_cases(
            query=RedboxQuery(
                question="What is AI?", file_uuids=[uuid4(), uuid4()], user_uuid=uuid4(), chat_history=[]
            ),
            test_data=[
                RedboxTestData(
                    2, 40_000, expected_llm_response=["Testing Response 1"], expected_route=ChatRoute.chat_with_docs
                ),
                RedboxTestData(
                    2, 80_000, expected_llm_response=["Testing Response 1"], expected_route=ChatRoute.chat_with_docs
                ),
                RedboxTestData(
                    2,
                    140_000,
                    expected_llm_response=["Map Step Response"] * 2 + ["Testing Response 1"],
                    expected_route=ChatRoute.chat_with_docs_map_reduce,
                ),
                RedboxTestData(
                    4,
                    140_000,
                    expected_llm_response=["Map Step Response"] * 4
                    + ["Merge Per Document Response"] * 2
                    + ["Testing Response 1"],
                    expected_route=ChatRoute.chat_with_docs_map_reduce,
                ),
            ],
            test_id="Chat with multiple docs",
        ),
        generate_test_cases(
            query=RedboxQuery(question="What is AI?", file_uuids=[uuid4()], user_uuid=uuid4(), chat_history=[]),
            test_data=[
                RedboxTestData(
                    2,
                    200_000,
                    expected_llm_response=["Map Step Response"] * 2
                    + ["Merge Per Document Response"]
                    + ["Testing Response 1"],
                    expected_route=ChatRoute.chat_with_docs_map_reduce,
                ),
            ],
            test_id="Chat with large doc",
        ),
        generate_test_cases(
            query=RedboxQuery(question="@search What is AI?", file_uuids=[uuid4()], user_uuid=uuid4(), chat_history=[]),
            test_data=[
                RedboxTestData(
                    1,
                    10000,
                    expected_llm_response=["Condense response", "The cake is a lie"],
                    expected_route=ChatRoute.search,
                ),
                RedboxTestData(
                    5,
                    10000,
                    expected_llm_response=["Condense response", "The cake is a lie"],
                    expected_route=ChatRoute.search,
                ),
            ],
            test_id="Search",
        ),
        generate_test_cases(
            query=RedboxQuery(
                question="@nosuchkeyword What is AI?", file_uuids=[uuid4()], user_uuid=uuid4(), chat_history=[]
            ),
            test_data=[
                RedboxTestData(
                    2,
                    200_000,
                    expected_llm_response=["That keyword isn't recognised"],
                    expected_route=ChatRoute.error_no_keyword,
                ),
            ],
            test_id="No Such Keyword",
        ),
    ]
    for test_case in generated_cases
]


@pytest.fixture(params=TEST_CASES, ids=[t.test_id for t in TEST_CASES])
def test_case(request: FixtureRequest) -> RedboxChatTestCase:
    return request.param


@pytest.fixture
def test_case_uploaded_docs(test_case: RedboxChatTestCase, es_store: ElasticsearchStore) -> Generator[None, None, None]:
    docs_ids = es_store.add_documents(test_case.docs)
    yield
    if docs_ids:
        es_store.delete(docs_ids)


@pytest.fixture
def test_case_query_headers(test_case: RedboxChatTestCase) -> dict[str, str]:
    return {"Authorization": f"Bearer {jwt.encode({"user_uuid": str(test_case.query.user_uuid)}, key="nvjkernd")}"}


def test_rag(
    test_case: RedboxChatTestCase,
    test_case_uploaded_docs: None,
    test_case_query_headers: dict[str, str],
    app_client: TestClient,
    mocker: MockerFixture,
):
    llm = GenericFakeChatModel(messages=iter(test_case.test_data.expected_llm_response))

    with (
        mocker.patch("redbox.graph.nodes.processes.get_chat_llm", return_value=llm),
    ):
        response = app_client.post(
            "/chat/rag",
            headers=test_case_query_headers,
            json={
                "message_history": [
                    {"role": message.role, "text": message.text} for message in test_case.query.chat_history
                ]
                + [{"role": "user", "text": test_case.query.question}],
                "selected_files": [{"uuid": str(file_uuid)} for file_uuid in test_case.query.file_uuids],
            },
        )
    assert response.status_code == 200, response.text
    chat_response = ChatResponse.model_validate(response.json())

    assert (
        chat_response.output_text == test_case.test_data.expected_llm_response[-1]
    ), f"Expected response [{test_case.test_data.expected_llm_response}] received [{chat_response.output_text}]"
    assert (
        chat_response.route_name == test_case.test_data.expected_route
    ), f"Expected route [{test_case.test_data.expected_route}] received [{chat_response.route_name}]"
    returned_document_texts = set([d.page_content for d in chat_response.source_documents])
    test_query_matching_document_texts = set([d.page_content for d in test_case.get_docs_matching_query()])
    unexpected_returned_documents = list(
        filter(
            lambda d: d.page_content in returned_document_texts - test_query_matching_document_texts,
            chat_response.source_documents,
        )
    )
    assert len(unexpected_returned_documents) == 0, f"Unexpected source docs in result {unexpected_returned_documents}"


def test_rag_chat_streamed(
    test_case: RedboxChatTestCase,
    test_case_uploaded_docs: None,
    test_case_query_headers: dict[str, str],
    app_client: TestClient,
    mocker: MockerFixture,
):
    llm = GenericFakeChatModel(messages=iter(test_case.test_data.expected_llm_response))
    with (
        app_client.websocket_connect("/chat/rag", headers=test_case_query_headers) as websocket,
        mocker.patch("redbox.graph.nodes.processes.get_chat_llm", return_value=llm),
    ):
        # When
        websocket.send_text(
            json.dumps(
                {
                    "message_history": [
                        {"role": message.role, "text": message.text} for message in test_case.query.chat_history
                    ]
                    + [{"role": "user", "text": test_case.query.question}],
                    "selected_files": [{"uuid": str(file_uuid)} for file_uuid in test_case.query.file_uuids],
                }
            )
        )

        all_text, docs, route_name = [], [], ""
        while True:
            try:
                actual = websocket.receive_json()
                if actual["resource_type"] == "text":
                    all_text.append(actual["data"])
                if actual["resource_type"] == "documents":
                    docs.extend(actual["data"])
                if actual["resource_type"] == "route_name":
                    route_name = actual["data"]
            except WebSocketDisconnect:
                break

        # Then
        text = "".join(all_text)
        assert (
            text == test_case.test_data.expected_llm_response[-1]
        ), f"Expected response [{test_case.test_data.expected_llm_response}] received [{text}]"
        assert (
            route_name == test_case.test_data.expected_route
        ), f"Expected route [{test_case.test_data.expected_route}] received [{route_name}]"
        returned_document_texts = set([d["page_content"] for d in docs])
        test_query_matching_document_texts = set([d.page_content for d in test_case.get_docs_matching_query()])
        unexpected_returned_documents = list(
            filter(lambda d: d["page_content"] in returned_document_texts - test_query_matching_document_texts, docs)
        )
        assert (
            len(unexpected_returned_documents) == 0
        ), f"Unexpected source docs in result {unexpected_returned_documents}"


def test_available_tools(app_client: TestClient, test_case_query_headers: dict[str, str]):
    response = app_client.get("/chat/tools", headers=test_case_query_headers)
    assert response.status_code == 200
    tool_definitions = response.json()
    assert len(tool_definitions) > 0
    assert EXPECTED_AVAILABLE_ROUTES == {item["name"] for item in tool_definitions}
    for tool_definition in tool_definitions:
        assert "name" in tool_definition
        assert "description" in tool_definition
