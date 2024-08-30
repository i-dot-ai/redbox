import pytest
from contextlib import nullcontext as does_not_raise
from uuid import uuid4
from pytest_mock import MockerFixture
from tiktoken.core import Encoding

from langgraph.graph import START, END, StateGraph
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.retrievers import BaseRetriever

from redbox.graph.nodes.processes import (
    build_chat_pattern,
    build_merge_pattern,
    build_set_route_pattern,
    build_retrieve_pattern,
    build_set_text_pattern,
    build_passthrough_pattern,
    build_stuff_pattern,
    empty_process,
    clear_documents_process,
)
from redbox.chains.runnables import build_chat_prompt_from_messages_runnable, build_llm_chain, CannedChatLLM
from redbox.test.data import (
    RedboxTestData,
    RedboxChatTestCase,
    generate_test_cases,
    generate_docs,
    mock_all_chunks_retriever,
    mock_parameterised_retriever,
)
from redbox.models.chat import ChatRoute
from redbox.models.chain import PromptSet, RedboxQuery, RedboxState
from redbox.transform import flatten_document_state, structure_documents


LANGGRAPH_DEBUG = True

CHAT_PROMPT_TEST_CASES = generate_test_cases(
    query=RedboxQuery(question="What is AI?", s3_keys=[], user_uuid=uuid4(), chat_history=[]),
    test_data=[
        RedboxTestData(0, 0, expected_llm_response=["Testing Response 1"], expected_route=ChatRoute.chat),
        RedboxTestData(
            2, 40_000, expected_llm_response=["Testing Response 1"], expected_route=ChatRoute.chat_with_docs
        ),
    ],
    test_id="Chat prompt runnable",
)


@pytest.mark.parametrize(("test_case"), CHAT_PROMPT_TEST_CASES, ids=[t.test_id for t in CHAT_PROMPT_TEST_CASES])
def test_build_chat_prompt_from_messages_runnable(test_case: RedboxChatTestCase, tokeniser: Encoding):
    """Tests a given state can be turned into a chat prompt."""
    chat_prompt = build_chat_prompt_from_messages_runnable(PromptSet.Chat, tokeniser)
    state = RedboxState(request=test_case.query, documents=test_case.docs)

    with does_not_raise():
        response = chat_prompt.invoke(state)
        messages = response.to_messages()
        assert isinstance(messages, list)
        assert len(messages) > 0


BUILD_LLM_TEST_CASES = generate_test_cases(
    query=RedboxQuery(question="What is AI?", file_uuids=[], user_uuid=uuid4(), chat_history=[]),
    test_data=[
        RedboxTestData(
            2, 40_000, expected_llm_response=["Testing Response 1"], expected_route=ChatRoute.chat_with_docs
        ),
    ],
    test_id="Build LLM runnable",
)


@pytest.mark.parametrize(("test_case"), BUILD_LLM_TEST_CASES, ids=[t.test_id for t in BUILD_LLM_TEST_CASES])
def test_build_llm_chain(test_case: RedboxChatTestCase):
    """Tests a given state can update the data and metadata correctly."""
    llm = GenericFakeChatModel(messages=iter(test_case.test_data.expected_llm_response))
    llm_chain = build_llm_chain(PromptSet.Chat, llm)
    state = RedboxState(request=test_case.query, documents=test_case.docs)

    final_state = llm_chain.invoke(state)

    assert (
        final_state["text"] == test_case.test_data.expected_llm_response[-1]
    ), f"Expected LLM response: '{test_case.test_data.expected_llm_response[-1]}'. Received '{final_state["text"]}'"
    assert sum(final_state["metadata"]["input_tokens"].values())
    assert sum(final_state["metadata"]["output_tokens"].values())


CHAT_TEST_CASES = generate_test_cases(
    query=RedboxQuery(question="What is AI?", s3_keys=[], user_uuid=uuid4(), chat_history=[]),
    test_data=[RedboxTestData(0, 0, expected_llm_response=["Testing Response 1"], expected_route=ChatRoute.chat)],
    test_id="Chat pattern",
)


@pytest.mark.parametrize(("test_case"), CHAT_TEST_CASES, ids=[t.test_id for t in CHAT_TEST_CASES])
def test_build_chat_pattern(test_case: RedboxChatTestCase, mocker: MockerFixture):
    """Tests a given state["request"] correctly changes state["text"]."""
    llm = GenericFakeChatModel(messages=iter(test_case.test_data.expected_llm_response))
    state = RedboxState(request=test_case.query, documents=[])

    chat = build_chat_pattern(prompt_set=PromptSet.Chat, final_response_chain=True)

    with (
        mocker.patch("redbox.graph.nodes.processes.get_chat_llm", return_value=llm),
    ):
        response = chat(state)
    final_state = RedboxState(response)

    assert (
        final_state["text"] == test_case.test_data.expected_llm_response[-1]
    ), f"Expected LLM response: '{test_case.test_data.expected_llm_response[-1]}'. Received '{final_state["text"]}'"


SET_ROUTE_TEST_CASES = generate_test_cases(
    query=RedboxQuery(question="What is AI?", s3_keys=[], user_uuid=uuid4(), chat_history=[]),
    test_data=[
        RedboxTestData(0, 0, expected_llm_response=["Testing Response 1"], expected_route=ChatRoute.chat),
        RedboxTestData(
            2, 40_000, expected_llm_response=["Testing Response 1"], expected_route=ChatRoute.chat_with_docs
        ),
    ],
    test_id="Set route pattern",
)


@pytest.mark.parametrize(("test_case"), SET_ROUTE_TEST_CASES, ids=[t.test_id for t in SET_ROUTE_TEST_CASES])
def test_build_set_route_pattern(test_case: RedboxChatTestCase):
    """Tests a given value correctly changes state["route"]."""
    set_route = build_set_route_pattern(route=test_case.test_data.expected_route)
    state = RedboxState(request=test_case.query, documents=[])

    response = set_route(state)
    final_state = RedboxState(response)

    assert (
        final_state["route_name"] == test_case.test_data.expected_route.value
    ), f"Expected Route: '{ test_case.test_data.expected_route.value}'. Received '{final_state["route_name"]}'"


RETRIEVER_TEST_CASES = generate_test_cases(
    query=RedboxQuery(question="What is AI?", s3_keys=["s3_key_1", "s3_key_2"], user_uuid=uuid4(), chat_history=[]),
    test_data=[
        RedboxTestData(
            2, 40_000, expected_llm_response=["Testing Response 1"], expected_route=ChatRoute.chat_with_docs
        ),
        RedboxTestData(
            2, 80_000, expected_llm_response=["Testing Response 1"], expected_route=ChatRoute.chat_with_docs
        ),
        RedboxTestData(
            4,
            140_000,
            expected_llm_response=["Map Step Response"] * 4 + ["Testing Response 1"],
            expected_route=ChatRoute.chat_with_docs,
        ),
    ],
    test_id="Retriever pattern",
)


@pytest.mark.parametrize(
    ("test_case", "mock_retriever"),
    [(test_case, mock_all_chunks_retriever) for test_case in RETRIEVER_TEST_CASES]
    + [(test_case, mock_parameterised_retriever) for test_case in RETRIEVER_TEST_CASES],
    ids=[f"All chunks, {t.test_id}" for t in RETRIEVER_TEST_CASES]
    + [f"Parameterised, {t.test_id}" for t in RETRIEVER_TEST_CASES],
)
def test_build_retrieve_pattern(test_case: RedboxChatTestCase, mock_retriever: BaseRetriever):
    """Tests a given state["request"] correctly changes state["documents"]."""
    retriever = mock_retriever(test_case.docs)
    retriever_function = build_retrieve_pattern(retriever=retriever)
    state = RedboxState(request=test_case.query, documents=[])

    response = retriever_function(state)
    final_state = RedboxState(response)

    assert final_state["documents"] == structure_documents(test_case.docs)


MERGE_TEST_CASES = generate_test_cases(
    query=RedboxQuery(question="What is AI?", s3_keys=["s3_key_1", "s3_key_2"], user_uuid=uuid4(), chat_history=[]),
    test_data=[
        RedboxTestData(
            2, 40_000, expected_llm_response=["Testing Response 1"], expected_route=ChatRoute.chat_with_docs
        ),
        RedboxTestData(
            4, 40_000, expected_llm_response=["Testing Response 2"], expected_route=ChatRoute.chat_with_docs
        ),
    ],
    test_id="Merge pattern",
)


@pytest.mark.parametrize(("test_case"), MERGE_TEST_CASES, ids=[t.test_id for t in MERGE_TEST_CASES])
def test_build_merge_pattern(test_case: RedboxChatTestCase, mocker: MockerFixture):
    """Tests a given state["request"] and state["documents"] correctly changes state["documents"]."""
    llm = GenericFakeChatModel(messages=iter(test_case.test_data.expected_llm_response))
    state = RedboxState(request=test_case.query, documents=structure_documents(test_case.docs))

    merge = build_merge_pattern(prompt_set=PromptSet.ChatwithDocsMapReduce, final_response_chain=True)

    with (
        mocker.patch("redbox.graph.nodes.processes.get_chat_llm", return_value=llm),
    ):
        response = merge(state)
    final_state = RedboxState(response)

    response_documents = [doc for doc in flatten_document_state(final_state["documents"]) if doc is not None]
    noned_documents = sum([1 for doc in final_state["documents"].values() for v in doc.values() if v is None])

    assert len(response_documents) == 1
    assert noned_documents == len(test_case.docs) - 1
    assert (
        response_documents[0].page_content == test_case.test_data.expected_llm_response[-1]
    ), f"Expected document content: '{test_case.test_data.expected_llm_response[-1]}'. Received '{response_documents[0].page_content}'"


STUFF_TEST_CASES = generate_test_cases(
    query=RedboxQuery(question="What is AI?", s3_keys=["s3_key_1", "s3_key_2"], user_uuid=uuid4(), chat_history=[]),
    test_data=[
        RedboxTestData(
            2, 40_000, expected_llm_response=["Testing Response 1"], expected_route=ChatRoute.chat_with_docs
        ),
        RedboxTestData(
            4, 40_000, expected_llm_response=["Testing Response 2"], expected_route=ChatRoute.chat_with_docs
        ),
    ],
    test_id="Stuff pattern",
)


@pytest.mark.parametrize(("test_case"), STUFF_TEST_CASES, ids=[t.test_id for t in STUFF_TEST_CASES])
def test_build_stuff_pattern(test_case: RedboxChatTestCase, mocker: MockerFixture):
    """Tests a given state["request"] and state["documents"] correctly changes state["text"]."""
    llm = GenericFakeChatModel(messages=iter(test_case.test_data.expected_llm_response))
    state = RedboxState(request=test_case.query, documents=structure_documents(test_case.docs))

    stuff = build_stuff_pattern(prompt_set=PromptSet.ChatwithDocs, final_response_chain=True)

    with (
        mocker.patch("redbox.graph.nodes.processes.get_chat_llm", return_value=llm),
    ):
        response = stuff(state)
    final_state = RedboxState(response)

    assert (
        final_state["text"] == test_case.test_data.expected_llm_response[-1]
    ), f"Expected LLM response: '{test_case.test_data.expected_llm_response[-1]}'. Received '{final_state["text"]}'"


def test_build_passthrough_pattern():
    """Tests a given state["request"] correctly changes state["text"]."""
    passthrough = build_passthrough_pattern()
    state = RedboxState(
        request=RedboxQuery(question="What is AI?", s3_keys=[], user_uuid=uuid4(), chat_history=[]),
    )

    response = passthrough(state)
    final_state = RedboxState(response)

    assert final_state["text"] == "What is AI?"


def test_build_set_text_pattern():
    """Tests a given value correctly changes the state["text"]."""
    set_text = build_set_text_pattern(text="An hendy hap ychabbe ychent.")
    state = RedboxState(
        request=RedboxQuery(question="What is AI?", s3_keys=[], user_uuid=uuid4(), chat_history=[]),
    )

    response = set_text(state)
    final_state = RedboxState(response)

    assert final_state["text"] == "An hendy hap ychabbe ychent."


def test_empty_process():
    """Tests the empty process doesn't touch the state whatsoever."""
    state = RedboxState(
        request=RedboxQuery(question="What is AI?", s3_keys=[], user_uuid=uuid4(), chat_history=[]),
        documents=structure_documents([doc for doc in generate_docs(s3_key="s3_key", creator_user_uuid=uuid4())]),
        text="Foo",
        route_name=ChatRoute.chat_with_docs_map_reduce,
    )

    builder = StateGraph(RedboxState)
    builder.add_node("null", empty_process)
    builder.add_edge(START, "null")
    builder.add_edge("null", END)
    graph = builder.compile()

    response = graph.invoke(state)
    final_state = RedboxState(response)

    assert final_state == state


CLEAR_DOC_TEST_CASES = [
    RedboxState(
        request=RedboxQuery(question="What is AI?", file_uuids=[], user_uuid=uuid4(), chat_history=[]),
        documents=structure_documents([doc for doc in generate_docs(s3_key="s3_key", creator_user_uuid=uuid4())]),
        text="Foo",
        route_name=ChatRoute.chat_with_docs_map_reduce,
    ),
    RedboxState(
        request=RedboxQuery(question="What is AI?", file_uuids=[], user_uuid=uuid4(), chat_history=[]),
        documents={},
        text="Foo",
        route_name=ChatRoute.chat_with_docs_map_reduce,
    ),
]


@pytest.mark.parametrize(("test_case"), CLEAR_DOC_TEST_CASES)
def test_clear_documents(test_case: list[RedboxState]):
    """Tests that clear documents does what it says."""
    builder = StateGraph(RedboxState)
    builder.add_node("clear", clear_documents_process)
    builder.add_edge(START, "clear")
    builder.add_edge("clear", END)
    graph = builder.compile()

    response = graph.invoke(test_case)
    final_state = RedboxState(response)

    assert final_state["documents"] == {}


def test_canned_llm():
    """Tests that the CannedLLM works in a normal call."""
    text = "Lorem ipsum dolor sit amet."
    canned = CannedChatLLM(text=text)
    response = canned.invoke("Foo")
    assert text == response.content


@pytest.mark.asyncio
async def test_canned_llm_async():
    """Tests that the CannedLLM works asynchronously."""
    text = "Lorem ipsum dolor sit amet."
    canned = CannedChatLLM(text=text)

    events: list[dict] = []
    async for e in canned.astream_events("Foo", version="v2"):
        events.append(e)

    response = "".join([d["data"]["chunk"].content for d in events if d.get("event") == "on_chat_model_stream"])

    assert text == response
