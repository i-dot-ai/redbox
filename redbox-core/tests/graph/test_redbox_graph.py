from uuid import uuid4
import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.runnables import RunnableLambda
import tiktoken

from redbox.models.chain import ChainInput, ChainState
from redbox.graph.root import get_redbox_graph, run_redbox
from redbox.models.chat import ChatRoute
from redbox.models.settings import Settings
from tests.graph.data import RedboxChatTestCase, TestData, generate_test_cases


LANGGRAPH_DEBUG = False

test_env = Settings()


@pytest.fixture(scope="session")
def env():
    return Settings()


@pytest.fixture(scope="session")
def tokeniser():
    return tiktoken.get_encoding("cl100k_base")


def all_chunks_retriever(docs):
    def mock_retrieve(query):
        return docs

    return RunnableLambda(mock_retrieve)


def parameterised_retriever(docs):
    def mock_retrieve(query):
        return docs

    return RunnableLambda(mock_retrieve)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("test_case"),
    [
        test_case
        for generated_cases in [
            generate_test_cases(
                query=ChainInput(question="What is AI?", file_uuids=[], user_uuid=uuid4(), chat_history=[]),
                test_data=[
                    TestData(0, 0, ["Testing Response 1"], ChatRoute.chat),
                    TestData(1, 100, ["Testing Response 1"], ChatRoute.chat),
                    TestData(10, 1200, ["Testing Response 1"], ChatRoute.chat),
                ],
            ),
            generate_test_cases(
                query=ChainInput(question="What is AI?", file_uuids=[uuid4()], user_uuid=uuid4(), chat_history=[]),
                test_data=[
                    TestData(1, 10000, ["Testing Response 1"], ChatRoute.chat_with_docs),
                    TestData(1, 80000, ["Testing Response 1"], ChatRoute.chat_with_docs),
                    TestData(1, 120000, ["Testing Response 1"], ChatRoute.chat_with_docs),
                ],
            ),
            generate_test_cases(
                query=ChainInput(question="What is AI?", file_uuids=[uuid4()], user_uuid=uuid4(), chat_history=[]),
                test_data=[
                    TestData(1, 10000, ["Testing Response 1"], ChatRoute.chat_with_docs),
                    TestData(1, 80000, ["Testing Response 1"], ChatRoute.chat_with_docs),
                    TestData(1, 120000, ["Testing Response 1"], ChatRoute.chat_with_docs),
                ],
            ),
            generate_test_cases(
                query=ChainInput(question="What is AI?", file_uuids=[uuid4()], user_uuid=uuid4(), chat_history=[]),
                test_data=[
                    TestData(
                        2, 200_000, ["Intermediate document"] * 2 + ["Testing Response 1"], ChatRoute.chat_with_docs
                    ),
                    TestData(
                        5, 80000, ["Intermediate document"] * 5 + ["Testing Response 1"], ChatRoute.chat_with_docs
                    ),
                    TestData(
                        10, 100_000, ["Intermediate document"] * 10 + ["Testing Response 1"], ChatRoute.chat_with_docs
                    ),
                ],
            ),
        ]
        for test_case in generated_cases
    ],
)
async def test_chat(test_case: RedboxChatTestCase, env, tokeniser):
    app = get_redbox_graph(
        llm=GenericFakeChatModel(messages=iter(test_case.llm_response)),
        all_chunks_retriever=all_chunks_retriever(test_case.docs),
        parameterised_retriever=parameterised_retriever(test_case.docs),
        tokeniser=tokeniser,
        env=env,
        debug=LANGGRAPH_DEBUG,
    )
    response = await run_redbox(
        input=ChainState(query=test_case.query),
        app=app,
    )
    final_state = ChainState(response)
    assert (
        final_state["response"] == test_case.llm_response[-1]
    ), f"Expected LLM response: '{test_case.llm_response[-1]}'. Received '{final_state["response"]}'"
    assert (
        final_state["route_name"] == test_case.expected_route
    ), f"Expected Route: '{ test_case.expected_route}'. Received '{final_state["route_name"]}'"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("test_case"),
    [
        test_case
        for generated_cases in [
            generate_test_cases(
                query=ChainInput(question="What is AI?", file_uuids=[], user_uuid=uuid4(), chat_history=[]),
                test_data=[
                    TestData(0, 0, ["The cake is a lie"], ChatRoute.chat),
                ],
            ),
            generate_test_cases(
                query=ChainInput(question="What is AI?", file_uuids=[uuid4()], user_uuid=uuid4(), chat_history=[]),
                test_data=[
                    TestData(1, 10000, ["The cake is a lie"], ChatRoute.chat_with_docs),
                    TestData(5, 10000, ["map_reduce_result"] * 5 + ["The cake is a lie"], ChatRoute.chat_with_docs),
                ],
            ),
            generate_test_cases(
                query=ChainInput(
                    question="@search What is AI?", file_uuids=[uuid4()], user_uuid=uuid4(), chat_history=[]
                ),
                test_data=[
                    TestData(1, 10000, ["The cake is a lie"], ChatRoute.search),
                    TestData(5, 10000, ["The cake is a lie"], ChatRoute.search),
                ],
            ),
        ]
        for test_case in generated_cases
    ],
)
async def test_streaming(test_case: RedboxChatTestCase, env, tokeniser):
    app = get_redbox_graph(
        llm=GenericFakeChatModel(messages=iter(test_case.llm_response)),
        all_chunks_retriever=all_chunks_retriever(test_case.docs),
        parameterised_retriever=parameterised_retriever(test_case.docs),
        tokeniser=tokeniser,
        env=env,
        debug=LANGGRAPH_DEBUG,
    )

    token_events = []

    def streaming_response_handler(tokens: str):
        token_events.append(tokens)

    response = await run_redbox(
        input=ChainState(query=test_case.query), app=app, response_tokens_callback=streaming_response_handler
    )
    final_state = ChainState(response)
    print(token_events)
    assert len(token_events) > 1, f"Expected tokens as a stream. Received: {token_events}"
    llm_response = "".join(token_events)
    assert (
        final_state["response"] == llm_response
    ), f"Expected LLM response: '{llm_response}'. Received '{final_state["response"]}'"
    assert (
        final_state["route_name"] == test_case.expected_route
    ), f"Expected Route: '{ test_case.expected_route}'. Received '{final_state["route_name"]}'"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("test_case"),
    [
        test_case
        for generated_cases in [
            generate_test_cases(
                query=ChainInput(question="@search What is AI?", file_uuids=[], user_uuid=uuid4(), chat_history=[]),
                test_data=[
                    TestData(0, 0, [test_env.response_no_doc_available], ChatRoute.search),
                ],
            ),
            generate_test_cases(
                query=ChainInput(question="What is AI?", file_uuids=[uuid4()], user_uuid=uuid4(), chat_history=[]),
                test_data=[
                    TestData(
                        2, 200_000, ["Intermediate document"] * 2 + ["Testing Response 1"], ChatRoute.chat_with_docs
                    ),
                    TestData(
                        5, 80000, ["Intermediate document"] * 5 + ["Testing Response 1"], ChatRoute.chat_with_docs
                    ),
                    TestData(
                        10, 100_000, ["Intermediate document"] * 10 + ["Testing Response 1"], ChatRoute.chat_with_docs
                    ),
                ],
            ),
        ]
        for test_case in generated_cases
    ],
)
async def test_search(test_case: RedboxChatTestCase, env, tokeniser):
    app = get_redbox_graph(
        llm=GenericFakeChatModel(messages=iter(test_case.llm_response)),
        all_chunks_retriever=all_chunks_retriever(test_case.docs),
        parameterised_retriever=parameterised_retriever(test_case.docs),
        tokeniser=tokeniser,
        env=env,
        debug=LANGGRAPH_DEBUG,
    )
    response = await run_redbox(input=ChainState(query=test_case.query), app=app)
    final_state = ChainState(response)
    assert (
        final_state["response"] == test_case.llm_response[-1]
    ), f"Expected LLM response: '{test_case.llm_response[-1]}'. Received '{final_state["response"]}'"
    assert (
        final_state["route_name"] == test_case.expected_route
    ), f"Expected Route: '{ test_case.expected_route}'. Received '{final_state["route_name"]}'"
