import copy
from uuid import uuid4

import pytest
from langchain_core.documents import Document
from langchain_core.messages import AIMessage
from pytest_mock import MockerFixture

from redbox import Redbox
from redbox.models.chain import (
    RedboxQuery,
    RedboxState,
    RequestMetadata,
    metadata_reducer,
)
from redbox.models.chat import ChatRoute, ErrorRoute
from redbox.models.graph import RedboxActivityEvent
from redbox.models.settings import Settings
from redbox.test.data import (
    GenericFakeChatModelWithTools,
    RedboxChatTestCase,
    RedboxTestData,
    generate_test_cases,
    mock_retriever,
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
                    llm_responses=["Testing Response 1"],
                    expected_route=ChatRoute.chat,
                ),
                RedboxTestData(
                    number_of_docs=1,
                    tokens_in_all_docs=100,
                    llm_responses=["Testing Response 1"],
                    expected_route=ChatRoute.chat,
                ),
                RedboxTestData(
                    number_of_docs=10,
                    tokens_in_all_docs=1200,
                    llm_responses=["Testing Response 1"],
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
                    llm_responses=["Testing Response 1"],
                    expected_route=ChatRoute.chat_with_docs,
                ),
                RedboxTestData(
                    number_of_docs=1,
                    tokens_in_all_docs=50_000,
                    llm_responses=["Testing Response 1"],
                    expected_route=ChatRoute.chat_with_docs,
                ),
                RedboxTestData(
                    number_of_docs=1,
                    tokens_in_all_docs=80_000,
                    llm_responses=["Testing Response 1"],
                    expected_route=ChatRoute.chat_with_docs,
                ),
            ],
            test_id="Chat with single doc",
        ),
        generate_test_cases(
            query=RedboxQuery(
                question="What is AI?", s3_keys=["s3_key_1", "s3_key_2"], user_uuid=uuid4(), chat_history=[]
            ),
            test_data=[
                RedboxTestData(
                    number_of_docs=2,
                    tokens_in_all_docs=40_000,
                    llm_responses=["Testing Response 1"],
                    expected_route=ChatRoute.chat_with_docs,
                ),
                RedboxTestData(
                    number_of_docs=2,
                    tokens_in_all_docs=80_000,
                    llm_responses=["Testing Response 1"],
                    expected_route=ChatRoute.chat_with_docs,
                ),
                RedboxTestData(
                    number_of_docs=2,
                    tokens_in_all_docs=140_000,
                    llm_responses=["These documents are too large to work with."] * 2
                    + ["These documents are too large to work with."],
                    expected_route=ErrorRoute.files_too_large,
                ),
                RedboxTestData(
                    number_of_docs=4,
                    tokens_in_all_docs=140_000,
                    llm_responses=["Map Step Response"] * 4
                    + ["Merge Per Document Response"] * 2
                    + ["These documents are too large to work with."],
                    expected_route=ErrorRoute.files_too_large,
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
                    number_of_docs=10,
                    tokens_in_all_docs=2_000_000,
                    llm_responses=["These documents are too large to work with."],
                    expected_route=ErrorRoute.files_too_large,
                ),
            ],
            test_id="Document too big for system",
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
                    llm_responses=["Testing Response 1"],
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
                    llm_responses=["Testing Response 1"],
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

    # Mock the LLM and relevant tools
    llm = GenericFakeChatModelWithTools(messages=iter(test_case.test_data.llm_responses))
    mocker.patch("redbox.graph.nodes.processes.get_chat_llm", return_value=llm)

    # Instantiate app
    app = Redbox(
        retriever=mock_retriever(test_case.docs),
        debug=LANGGRAPH_DEBUG,
    )

    # Define callback functions
    token_events = []
    metadata_events = []
    route_name = None

    async def streaming_response_handler(tokens: str):
        token_events.append(tokens)

    async def metadata_response_handler(metadata: dict):
        metadata_events.append(metadata)

    async def streaming_route_name_handler(route: str):
        nonlocal route_name
        route_name = route


    # Run the app
    final_state = await app.run(
        input=RedboxState(request=test_case.query),
        response_tokens_callback=streaming_response_handler,
        metadata_tokens_callback=metadata_response_handler,
        route_name_callback=streaming_route_name_handler,
    )

    # Assertions
    assert route_name is not None, f"No Route Name event fired! - Final State: {final_state}"

    # Bit of a bodge to retain the ability to check that the LLM streaming is working in most cases
    if not route_name.startswith("error"):
        assert (
            len(token_events) > 1
        ), f"Expected tokens as a stream. Received: {token_events}"  # Temporarily turning off streaming check
        assert len(metadata_events) == len(
            test_case.test_data.llm_responses
        ), f"Expected {len(test_case.test_data.llm_responses)} metadata events. Received {len(metadata_events)}"


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

    expected_text = (
        test.test_data.expected_text if test.test_data.expected_text is not None else test.test_data.llm_responses[-1]
    )
    expected_text = expected_text.content if isinstance(expected_text, AIMessage) else expected_text

    assert (
        final_state.last_message.content == llm_response
    ), f"Text response from streaming: '{llm_response}' did not match final state text '{final_state.last_message.content}'"
    assert (
        final_state.last_message.content == expected_text
    ), f"Expected text: '{expected_text}' did not match received text '{final_state.last_message.content}'"

    assert (
        final_state.route_name == test_case.test_data.expected_route
    ), f"Expected Route: '{ test_case.test_data.expected_route}'. Received '{final_state.route_name}'"
    if metadata := final_state.metadata:
        assert metadata == metadata_response, f"Expected metadata: '{metadata_response}'. Received '{metadata}'"
