import copy
from uuid import uuid4

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from pytest_mock import MockerFixture
from tiktoken.core import Encoding

from redbox import Redbox
from redbox.models.chain import AISettings, RedboxQuery, RedboxState, RequestMetadata, metadata_reducer
from redbox.models.chat import ChatRoute, ErrorRoute
from redbox.models.graph import RedboxActivityEvent
from redbox.models.settings import Settings
from redbox.test.data import (
    RedboxChatTestCase,
    RedboxTestData,
    generate_test_cases,
    mock_all_chunks_retriever,
    mock_metadata_retriever,
    mock_parameterised_retriever,
)

LANGGRAPH_DEBUG = True

SELF_ROUTE_TO_SEARCH = ["Condense self route question", "Testing Response - Search"]
SELF_ROUTE_TO_CHAT = ["Condense self route question", "unanswerable"]


def assert_number_of_events(num_of_events: int):
    return lambda events_list: len(events_list) == num_of_events


TEST_CASES = [
    test_case
    for generated_cases in [
        generate_test_cases(
            query=RedboxQuery(
                question="What is AI?", s3_keys=[], user_uuid=uuid4(), chat_history=[], permitted_s3_keys=[]
            ),
            test_data=[
                RedboxTestData(
                    number_of_docs=0,
                    tokens_in_all_docs=0,
                    expected_llm_response=["Testing Response 1"],
                    expected_route=ChatRoute.chat,
                ),
                RedboxTestData(
                    number_of_docs=1,
                    tokens_in_all_docs=100,
                    expected_llm_response=["Testing Response 1"],
                    expected_route=ChatRoute.chat,
                ),
                RedboxTestData(
                    number_of_docs=10,
                    tokens_in_all_docs=1200,
                    expected_llm_response=["Testing Response 1"],
                    expected_route=ChatRoute.chat,
                ),
            ],
            test_id="Basic Chat",
        ),
        generate_test_cases(
            query=RedboxQuery(
                question="What is AI?", s3_keys=["s3_key"], user_uuid=uuid4(), chat_history=[], permitted_s3_keys=[]
            ),
            test_data=[
                RedboxTestData(
                    number_of_docs=1,
                    tokens_in_all_docs=1_000,
                    expected_llm_response=["Testing Response 1"],
                    expected_route=ChatRoute.chat_with_docs,
                ),
                RedboxTestData(
                    number_of_docs=1,
                    tokens_in_all_docs=50_000,
                    expected_llm_response=["Testing Response 1"],
                    expected_route=ChatRoute.chat_with_docs,
                ),
                RedboxTestData(
                    number_of_docs=1,
                    tokens_in_all_docs=80_000,
                    expected_llm_response=["Testing Response 1"],
                    expected_route=ChatRoute.chat_with_docs,
                ),
            ],
            test_id="Chat with single doc",
        ),
        generate_test_cases(
            query=RedboxQuery(
                question="What is AI?",
                s3_keys=["s3_key_1", "s3_key_2"],
                user_uuid=uuid4(),
                chat_history=[],
                permitted_s3_keys=["s3_key_1", "s3_key_2"],
                ai_settings=AISettings(self_route_enabled=True),
            ),
            test_data=[
                RedboxTestData(
                    number_of_docs=2,
                    tokens_in_all_docs=40_000,
                    expected_llm_response=["Testing Response 1"],
                    expected_route=ChatRoute.chat_with_docs,
                ),
                RedboxTestData(
                    number_of_docs=2,
                    tokens_in_all_docs=80_000,
                    expected_llm_response=["Testing Response 1"],
                    expected_route=ChatRoute.chat_with_docs,
                ),
                RedboxTestData(
                    number_of_docs=2,
                    tokens_in_all_docs=140_000,
                    expected_llm_response=SELF_ROUTE_TO_CHAT + ["Map Step Response"] * 2 + ["Testing Response 1"],
                    expected_route=ChatRoute.chat_with_docs_map_reduce,
                    expected_activity_events=assert_number_of_events(1),
                ),
                RedboxTestData(
                    number_of_docs=4,
                    tokens_in_all_docs=140_000,
                    expected_llm_response=SELF_ROUTE_TO_CHAT
                    + ["Map Step Response"] * 4
                    + ["Merge Per Document Response"] * 2
                    + ["Testing Response 1"],
                    expected_route=ChatRoute.chat_with_docs_map_reduce,
                    expected_activity_events=assert_number_of_events(1),
                ),
            ],
            test_id="Chat with multiple docs - with self route",
        ),
        generate_test_cases(
            query=RedboxQuery(
                question="What is AI?", s3_keys=["s3_key_1", "s3_key_2"], user_uuid=uuid4(), chat_history=[]
            ),
            test_data=[
                RedboxTestData(
                    number_of_docs=2,
                    tokens_in_all_docs=40_000,
                    expected_llm_response=["Testing Response 1"],
                    expected_route=ChatRoute.chat_with_docs,
                ),
                RedboxTestData(
                    number_of_docs=2,
                    tokens_in_all_docs=80_000,
                    expected_llm_response=["Testing Response 1"],
                    expected_route=ChatRoute.chat_with_docs,
                ),
                RedboxTestData(
                    number_of_docs=2,
                    tokens_in_all_docs=140_000,
                    expected_llm_response=["Map Step Response"] * 2 + ["Testing Response 1"],
                    expected_route=ChatRoute.chat_with_docs_map_reduce,
                ),
                RedboxTestData(
                    number_of_docs=4,
                    tokens_in_all_docs=140_000,
                    expected_llm_response=["Map Step Response"] * 4
                    + ["Merge Per Document Response"] * 2
                    + ["Testing Response 1"],
                    expected_route=ChatRoute.chat_with_docs_map_reduce,
                ),
            ],
            test_id="Chat with multiple docs",
        ),
        generate_test_cases(
            query=RedboxQuery(
                question="What is AI?",
                s3_keys=["s3_key"],
                user_uuid=uuid4(),
                chat_history=[],
                permitted_s3_keys=["s3_key"],
            ),
            test_data=[
                RedboxTestData(
                    number_of_docs=2,
                    tokens_in_all_docs=200_000,
                    expected_llm_response=["Map Step Response"] * 2
                    + ["Merge Per Document Response"]
                    + ["Testing Response 1"],
                    expected_route=ChatRoute.chat_with_docs_map_reduce,
                ),
            ],
            test_id="Chat with large doc",
        ),
        generate_test_cases(
            query=RedboxQuery(
                question="What is AI?",
                s3_keys=["s3_key"],
                user_uuid=uuid4(),
                chat_history=[],
                ai_settings=AISettings(self_route_enabled=True),
            ),
            test_data=[
                RedboxTestData(
                    number_of_docs=2,
                    tokens_in_all_docs=200_000,
                    expected_llm_response=SELF_ROUTE_TO_CHAT
                    + ["Map Step Response"] * 2
                    + ["Merge Per Document Response"]
                    + ["Testing Response 1"],
                    expected_route=ChatRoute.chat_with_docs_map_reduce,
                    expected_activity_events=assert_number_of_events(1),
                ),
            ],
            test_id="Chat with large doc - with self route",
        ),
        generate_test_cases(
            query=RedboxQuery(
                question="What is AI?",
                s3_keys=["s3_key"],
                user_uuid=uuid4(),
                chat_history=[],
                permitted_s3_keys=["s3_key"],
                ai_settings=AISettings(self_route_enabled=True),
            ),
            test_data=[
                RedboxTestData(
                    number_of_docs=2,
                    tokens_in_all_docs=200_000,
                    expected_llm_response=SELF_ROUTE_TO_SEARCH,  # + ["Condense Question", "Testing Response 1"],
                    expected_route=ChatRoute.search,
                    expected_activity_events=assert_number_of_events(1),
                ),
            ],
            test_id="Self Route Search large doc",
        ),
        generate_test_cases(
            query=RedboxQuery(
                question="What is AI?",
                s3_keys=["s3_key"],
                user_uuid=uuid4(),
                chat_history=[],
                permitted_s3_keys=["s3_key"],
            ),
            test_data=[
                RedboxTestData(
                    number_of_docs=10,
                    tokens_in_all_docs=2_000_000,
                    expected_llm_response=["These documents are too large to work with."],
                    expected_route=ErrorRoute.files_too_large,
                ),
            ],
            test_id="Document too big for system",
        ),
        generate_test_cases(
            query=RedboxQuery(
                question="@search What is AI?",
                s3_keys=["s3_key"],
                user_uuid=uuid4(),
                chat_history=[],
                permitted_s3_keys=["s3_key"],
            ),
            test_data=[
                RedboxTestData(
                    number_of_docs=1,
                    tokens_in_all_docs=10000,
                    expected_llm_response=["Condense response", "The cake is a lie"],
                    expected_route=ChatRoute.search,
                ),
                RedboxTestData(
                    number_of_docs=5,
                    tokens_in_all_docs=10000,
                    expected_llm_response=["Condense response", "The cake is a lie"],
                    expected_route=ChatRoute.search,
                ),
            ],
            test_id="Search",
        ),
        generate_test_cases(
            query=RedboxQuery(
                question="@nosuchkeyword What is AI?",
                s3_keys=[],
                user_uuid=uuid4(),
                chat_history=[],
                permitted_s3_keys=[],
            ),
            test_data=[
                RedboxTestData(
                    number_of_docs=10,
                    tokens_in_all_docs=1000,
                    expected_llm_response=["Testing Response 1"],
                    expected_route=ChatRoute.chat,
                ),
            ],
            test_id="No Such Keyword",
        ),
        generate_test_cases(
            query=RedboxQuery(
                question="@nosuchkeyword What is AI?",
                s3_keys=["s3_key"],
                user_uuid=uuid4(),
                chat_history=[],
                permitted_s3_keys=["s3_key"],
            ),
            test_data=[
                RedboxTestData(
                    number_of_docs=1,
                    tokens_in_all_docs=50_000,
                    expected_llm_response=["Testing Response 1"],
                    expected_route=ChatRoute.chat_with_docs,
                ),
            ],
            test_id="No Such Keyword with docs",
        ),
    ]
    for test_case in generated_cases
]


@pytest.mark.asyncio
@pytest.mark.parametrize(("test"), TEST_CASES, ids=[t.test_id for t in TEST_CASES])
async def test_streaming(test: RedboxChatTestCase, env: Settings, mocker: MockerFixture):
    # Current setup modifies test data as it's not a fixture. This is a hack
    test_case = copy.deepcopy(test)

    app = Redbox(
        all_chunks_retriever=mock_all_chunks_retriever(test_case.docs),
        parameterised_retriever=mock_parameterised_retriever(test_case.docs),
        metadata_retriever=mock_metadata_retriever(test_case.docs),
        env=env,
        debug=LANGGRAPH_DEBUG,
    )

    # Define callback functions
    token_events = []
    metadata_events = []
    activity_events = []
    route_name = None

    async def streaming_response_handler(tokens: str):
        token_events.append(tokens)

    async def metadata_response_handler(metadata: dict):
        metadata_events.append(metadata)

    async def streaming_route_name_handler(route: str):
        nonlocal route_name
        route_name = route

    async def streaming_activity_handler(activity_event: RedboxActivityEvent):
        activity_events.append(activity_event)

    llm = GenericFakeChatModel(messages=iter(test_case.test_data.expected_llm_response))

    (mocker.patch("redbox.graph.nodes.processes.get_chat_llm", return_value=llm),)
    response = await app.run(
        input=RedboxState(request=test_case.query),
        response_tokens_callback=streaming_response_handler,
        metadata_tokens_callback=metadata_response_handler,
        route_name_callback=streaming_route_name_handler,
        activity_event_callback=streaming_activity_handler,
    )

    final_state = RedboxState(response)

    assert route_name is not None, f"No Route Name event fired! - Final State: {final_state}"

    # Bit of a bodge to retain the ability to check that the LLM streaming is working in most cases
    if not route_name.startswith("error"):
        assert len(token_events) > 1, f"Expected tokens as a stream. Received: {token_events}"
        assert len(metadata_events) == len(
            test_case.test_data.expected_llm_response
        ), f"Expected {len(test_case.test_data.expected_llm_response)} metadata events. Received {len(metadata_events)}"

    assert test_case.test_data.expected_activity_events(
        activity_events
    ), f"Activity events not as expected. Received: {activity_events}"

    llm_response = "".join(token_events)
    number_of_selected_files = len(test_case.query.s3_keys)
    metadata_response = metadata_reducer(
        RequestMetadata(
            selected_files_total_tokens=0
            if number_of_selected_files == 0
            else (int(test_case.test_data.tokens_in_all_docs / number_of_selected_files) * number_of_selected_files),
            number_of_selected_files=number_of_selected_files,
        ),
        metadata_events,
    )

    assert (
        final_state["text"] == llm_response
    ), f"Expected LLM response: '{llm_response}'. Received '{final_state["text"]}'"
    assert (
        final_state.get("route_name") == test_case.test_data.expected_route
    ), f"Expected Route: '{ test_case.test_data.expected_route}'. Received '{final_state["route_name"]}'"
    if metadata := final_state.get("metadata"):
        assert metadata == metadata_response, f"Expected metadata: '{metadata_response}'. Received '{metadata}'"


def test_get_available_keywords(tokeniser: Encoding, env: Settings):
    app = Redbox(
        all_chunks_retriever=mock_all_chunks_retriever([]),
        parameterised_retriever=mock_parameterised_retriever([]),
        metadata_retriever=mock_metadata_retriever([]),
        env=env,
        debug=LANGGRAPH_DEBUG,
    )
    keywords = {ChatRoute.search}

    assert keywords == set(app.get_available_keywords().keys())
