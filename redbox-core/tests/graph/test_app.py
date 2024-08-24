from uuid import uuid4
import pytest
import copy

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel

from redbox.models.chain import RedboxQuery, RedboxState
from redbox import Redbox
from redbox.models.chat import ChatRoute
from redbox.models.settings import Settings
from redbox.test.data import (
    RedboxTestData,
    RedboxChatTestCase,
    generate_test_cases,
    mock_all_chunks_retriever,
    mock_parameterised_retriever,
)


LANGGRAPH_DEBUG = True

test_env = Settings()

TEST_CASES = [
    test_case
    for generated_cases in [
        generate_test_cases(
            query=RedboxQuery(question="What is AI?", s3_keys=[], user_uuid=uuid4(), chat_history=[]),
            test_data=[
                RedboxTestData(0, 0, expected_llm_response=["Testing Response 1"], expected_route=ChatRoute.chat),
                RedboxTestData(1, 100, expected_llm_response=["Testing Response 1"], expected_route=ChatRoute.chat),
                RedboxTestData(10, 1200, expected_llm_response=["Testing Response 1"], expected_route=ChatRoute.chat),
            ],
            test_id="Basic Chat",
        ),
        generate_test_cases(
            query=RedboxQuery(question="What is AI?", s3_keys=["s3_key"], user_uuid=uuid4(), chat_history=[]),
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
                question="What is AI?", s3_keys=["s3_url_1", "s3_url_2"], user_uuid=uuid4(), chat_history=[]
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
            query=RedboxQuery(question="What is AI?", s3_keys=["s3_url"], user_uuid=uuid4(), chat_history=[]),
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
            query=RedboxQuery(question="What is AI?", s3_keys=["s3_url"], user_uuid=uuid4(), chat_history=[]),
            test_data=[
                RedboxTestData(
                    10,
                    2_000_000,
                    expected_llm_response=["These documents are too large to work with."],
                    expected_route=None,
                ),
            ],
            test_id="Document too big for system",
        ),
        generate_test_cases(
            query=RedboxQuery(question="@search What is AI?", s3_keys=["s3_url"], user_uuid=uuid4(), chat_history=[]),
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
                question="@nosuchkeyword What is AI?", s3_keys=["s3_url"], user_uuid=uuid4(), chat_history=[]
            ),
            test_data=[
                RedboxTestData(
                    2,
                    200_000,
                    expected_llm_response=[test_env.response_no_such_keyword],
                    expected_route=ChatRoute.error_no_keyword,
                ),
            ],
            test_id="No Such Keyword",
        ),
    ]
    for test_case in generated_cases
]


@pytest.fixture(scope="session")
def env():
    return Settings()


@pytest.mark.asyncio
@pytest.mark.parametrize(("test"), TEST_CASES, ids=[t.test_id for t in TEST_CASES])
async def test_chat(test: RedboxChatTestCase, env, mocker):
    # Current setup modifies test data as it's not a fixture. This is a hack
    test_case = copy.deepcopy(test)

    app = Redbox(
        all_chunks_retriever=mock_all_chunks_retriever(test_case.docs),
        parameterised_retriever=mock_parameterised_retriever(test_case.docs),
        env=env,
        debug=LANGGRAPH_DEBUG,
    )

    llm = GenericFakeChatModel(messages=iter(test_case.test_data.expected_llm_response))
    with (
        mocker.patch("redbox.graph.nodes.processes.get_chat_llm", return_value=llm),
    ):
        response = await app.run(input=RedboxState(request=test_case.query))

    final_state = RedboxState(response)
    assert (
        final_state["text"] == test_case.test_data.expected_llm_response[-1]
    ), f"Expected LLM response: '{test_case.test_data.expected_llm_response[-1]}'. Received '{final_state["text"]}'"
    assert (
        final_state["route_name"] == test_case.test_data.expected_route
    ), f"Expected Route: '{ test_case.test_data.expected_route}'. Received '{final_state["route_name"]}'"


@pytest.mark.asyncio
@pytest.mark.parametrize(("test"), TEST_CASES, ids=[t.test_id for t in TEST_CASES])
async def test_streaming(test: RedboxChatTestCase, env, mocker):
    # Current setup modifies test data as it's not a fixture. This is a hack
    test_case = copy.deepcopy(test)

    app = Redbox(
        all_chunks_retriever=mock_all_chunks_retriever(test_case.docs),
        parameterised_retriever=mock_parameterised_retriever(test_case.docs),
        env=env,
        debug=LANGGRAPH_DEBUG,
    )

    token_events = []

    async def streaming_response_handler(tokens: str):
        token_events.append(tokens)

    llm = GenericFakeChatModel(messages=iter(test_case.test_data.expected_llm_response))
    with (
        mocker.patch("redbox.graph.nodes.processes.get_chat_llm", return_value=llm),
    ):
        response = await app.run(
            input=RedboxState(request=test_case.query), response_tokens_callback=streaming_response_handler
        )

    final_state = RedboxState(response)

    # Bit of a bodge to retain the ability to check that the LLM streaming is working in most cases
    if not (final_state["route_name"] or "").startswith("error"):
        assert len(token_events) > 1, f"Expected tokens as a stream. Received: {token_events}"

    llm_response = "".join(token_events)

    assert (
        final_state["text"] == llm_response
    ), f"Expected LLM response: '{llm_response}'. Received '{final_state["text"]}'"
    assert (
        final_state["route_name"] == test_case.test_data.expected_route
    ), f"Expected Route: '{ test_case.test_data.expected_route}'. Received '{final_state["route_name"]}'"


def test_get_available_keywords(tokeniser):
    app = Redbox(
        all_chunks_retriever=mock_all_chunks_retriever([]),
        parameterised_retriever=mock_parameterised_retriever([]),
        env=env,
        debug=LANGGRAPH_DEBUG,
    )
    keywords = {ChatRoute.search}

    assert keywords == set(app.get_available_keywords().keys())
