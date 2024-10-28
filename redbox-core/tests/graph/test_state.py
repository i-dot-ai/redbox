from datetime import UTC, datetime, timedelta, timezone
from uuid import uuid4

import pytest
from langchain_core.documents import Document
from langchain_core.messages import ToolCall

from redbox.models.chain import (
    AISettings,
    DocumentState,
    LLMCallMetadata,
    RedboxQuery,
    RedboxState,
    RequestMetadata,
    ToolState,
    document_reducer,
    merge_redbox_state_updates,
    metadata_reducer,
    tool_calls_reducer,
)

GROUP_IDS = [uuid4() for _ in range(4)]
DOCUMENT_IDS = [uuid4() for _ in range(10)]


@pytest.mark.parametrize(
    argnames=("a", "b", "expected"),
    ids=[
        "Clear a document",
        "Clear a group",
        "Add a document",
        "Add a group",
        "Add and clear documents in one group",
        "Add and clear a group",
        "Add and clear documents across multiple groups",
    ],
    argvalues=[
        (
            {
                GROUP_IDS[0]: {DOCUMENT_IDS[0]: Document("a"), DOCUMENT_IDS[1]: Document("b")},
                GROUP_IDS[1]: {DOCUMENT_IDS[2]: Document("c"), DOCUMENT_IDS[3]: Document("d")},
            },
            {
                GROUP_IDS[0]: {
                    DOCUMENT_IDS[1]: None,
                }
            },
            {
                GROUP_IDS[0]: {
                    DOCUMENT_IDS[0]: Document("a"),
                },
                GROUP_IDS[1]: {DOCUMENT_IDS[2]: Document("c"), DOCUMENT_IDS[3]: Document("d")},
            },
        ),
        (
            {
                GROUP_IDS[0]: {DOCUMENT_IDS[0]: Document("a"), DOCUMENT_IDS[1]: Document("b")},
                GROUP_IDS[1]: {DOCUMENT_IDS[2]: Document("c"), DOCUMENT_IDS[3]: Document("d")},
            },
            {GROUP_IDS[0]: None},
            {GROUP_IDS[1]: {DOCUMENT_IDS[2]: Document("c"), DOCUMENT_IDS[3]: Document("d")}},
        ),
        (
            {
                GROUP_IDS[0]: {DOCUMENT_IDS[0]: Document("a"), DOCUMENT_IDS[1]: Document("b")},
                GROUP_IDS[1]: {DOCUMENT_IDS[2]: Document("c"), DOCUMENT_IDS[3]: Document("d")},
            },
            {
                GROUP_IDS[0]: {
                    DOCUMENT_IDS[4]: Document("e"),
                }
            },
            {
                GROUP_IDS[0]: {
                    DOCUMENT_IDS[0]: Document("a"),
                    DOCUMENT_IDS[1]: Document("b"),
                    DOCUMENT_IDS[4]: Document("e"),
                },
                GROUP_IDS[1]: {DOCUMENT_IDS[2]: Document("c"), DOCUMENT_IDS[3]: Document("d")},
            },
        ),
        (
            {
                GROUP_IDS[0]: {DOCUMENT_IDS[0]: Document("a"), DOCUMENT_IDS[1]: Document("b")},
                GROUP_IDS[1]: {DOCUMENT_IDS[2]: Document("c"), DOCUMENT_IDS[3]: Document("d")},
            },
            {GROUP_IDS[0]: {DOCUMENT_IDS[1]: None, DOCUMENT_IDS[4]: Document("e")}},
            {
                GROUP_IDS[0]: {DOCUMENT_IDS[0]: Document("a"), DOCUMENT_IDS[4]: Document("e")},
                GROUP_IDS[1]: {DOCUMENT_IDS[2]: Document("c"), DOCUMENT_IDS[3]: Document("d")},
            },
        ),
        (
            {
                GROUP_IDS[0]: {DOCUMENT_IDS[0]: Document("a"), DOCUMENT_IDS[1]: Document("b")},
                GROUP_IDS[1]: {DOCUMENT_IDS[2]: Document("c"), DOCUMENT_IDS[3]: Document("d")},
            },
            {GROUP_IDS[2]: {DOCUMENT_IDS[4]: Document("e"), DOCUMENT_IDS[5]: Document("f")}},
            {
                GROUP_IDS[0]: {DOCUMENT_IDS[0]: Document("a"), DOCUMENT_IDS[1]: Document("b")},
                GROUP_IDS[1]: {DOCUMENT_IDS[2]: Document("c"), DOCUMENT_IDS[3]: Document("d")},
                GROUP_IDS[2]: {DOCUMENT_IDS[4]: Document("e"), DOCUMENT_IDS[5]: Document("f")},
            },
        ),
        (
            {
                GROUP_IDS[0]: {DOCUMENT_IDS[0]: Document("a"), DOCUMENT_IDS[1]: Document("b")},
                GROUP_IDS[1]: {DOCUMENT_IDS[2]: Document("c"), DOCUMENT_IDS[3]: Document("d")},
            },
            {GROUP_IDS[0]: None, GROUP_IDS[2]: {DOCUMENT_IDS[4]: Document("e"), DOCUMENT_IDS[5]: Document("f")}},
            {
                GROUP_IDS[1]: {DOCUMENT_IDS[2]: Document("c"), DOCUMENT_IDS[3]: Document("d")},
                GROUP_IDS[2]: {DOCUMENT_IDS[4]: Document("e"), DOCUMENT_IDS[5]: Document("f")},
            },
        ),
        (
            {
                GROUP_IDS[0]: {DOCUMENT_IDS[0]: Document("a"), DOCUMENT_IDS[1]: Document("b")},
                GROUP_IDS[1]: {DOCUMENT_IDS[2]: Document("c"), DOCUMENT_IDS[3]: Document("d")},
            },
            {
                GROUP_IDS[0]: {DOCUMENT_IDS[0]: None, DOCUMENT_IDS[6]: Document("g")},
                GROUP_IDS[1]: {DOCUMENT_IDS[2]: None, DOCUMENT_IDS[3]: None, DOCUMENT_IDS[7]: Document("h")},
            },
            {
                GROUP_IDS[0]: {DOCUMENT_IDS[1]: Document("b"), DOCUMENT_IDS[6]: Document("g")},
                GROUP_IDS[1]: {DOCUMENT_IDS[7]: Document("h")},
            },
        ),
    ],
)
def test_document_reducer(a: DocumentState, b: DocumentState, expected: DocumentState):
    result = document_reducer(a, b)
    assert result == expected, f"Expected: {expected}. Result: {result}"


now = datetime.now(UTC)
GPT_4o_multiple_calls_1 = [
    LLMCallMetadata(llm_model_name="gpt-4o", input_tokens=0, output_tokens=0, timestamp=now - timedelta(days=10)),
    LLMCallMetadata(llm_model_name="gpt-4o", input_tokens=10, output_tokens=10, timestamp=now - timedelta(days=9)),
    LLMCallMetadata(llm_model_name="gpt-4o", input_tokens=10, output_tokens=10, timestamp=now - timedelta(days=8)),
]

GPT_4o_multiple_calls_1a = GPT_4o_multiple_calls_1 + [
    LLMCallMetadata(llm_model_name="gpt-4o", input_tokens=50, output_tokens=50, timestamp=now - timedelta(days=7)),
    LLMCallMetadata(llm_model_name="gpt-4o", input_tokens=60, output_tokens=60, timestamp=now - timedelta(days=6)),
]

GPT_4o_multiple_calls_2 = [
    LLMCallMetadata(llm_model_name="gpt-4o", input_tokens=100, output_tokens=200, timestamp=now - timedelta(days=5)),
    LLMCallMetadata(llm_model_name="gpt-4o", input_tokens=0, output_tokens=10, timestamp=now - timedelta(days=4)),
    LLMCallMetadata(llm_model_name="gpt-4o", input_tokens=100, output_tokens=210, timestamp=now - timedelta(days=3)),
]

multiple_models_multiple_calls_1 = [
    LLMCallMetadata(llm_model_name="gpt-4o", input_tokens=100, output_tokens=200, timestamp=now - timedelta(days=2)),
    LLMCallMetadata(llm_model_name="gpt-3.5", input_tokens=20, output_tokens=20, timestamp=now - timedelta(days=1)),
    LLMCallMetadata(llm_model_name="gpt-4o", input_tokens=100, output_tokens=210, timestamp=now - timedelta(hours=10)),
]

multiple_models_multiple_calls_1a = multiple_models_multiple_calls_1 + [
    LLMCallMetadata(llm_model_name="gpt-4o", input_tokens=300, output_tokens=310, timestamp=now - timedelta(hours=1)),
]


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        (
            RequestMetadata(llm_calls=GPT_4o_multiple_calls_1),
            RequestMetadata(llm_calls=GPT_4o_multiple_calls_2),
            RequestMetadata(
                llm_calls=sorted(GPT_4o_multiple_calls_1 + GPT_4o_multiple_calls_2, key=lambda c: c.timestamp)
            ),
        ),
        (
            RequestMetadata(llm_calls=GPT_4o_multiple_calls_1),
            RequestMetadata(llm_calls=GPT_4o_multiple_calls_1a),
            RequestMetadata(llm_calls=GPT_4o_multiple_calls_1a),
        ),
        (
            RequestMetadata(llm_calls=multiple_models_multiple_calls_1),
            RequestMetadata(llm_calls=GPT_4o_multiple_calls_2),
            RequestMetadata(
                llm_calls=sorted(GPT_4o_multiple_calls_2 + multiple_models_multiple_calls_1, key=lambda c: c.timestamp)
            ),
        ),
        (
            RequestMetadata(llm_calls=GPT_4o_multiple_calls_1),
            RequestMetadata(llm_calls=GPT_4o_multiple_calls_1a),
            RequestMetadata(llm_calls=GPT_4o_multiple_calls_1a),
        ),
    ],
)
def test_metadata_reducer(a: RequestMetadata, b: RequestMetadata, expected: RequestMetadata):
    result = metadata_reducer(a, b)
    assert result == expected, f"Expected: {expected}. Result: {result}"


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        (
            ToolState(
                {
                    "foo": {"tool": ToolCall({"name": "foo", "args": {"a": 1, "b": 2}, "id": "123"}), "called": False},
                    "bar": {
                        "tool": ToolCall({"name": "bar", "args": {"x": 10, "y": 20}, "id": "456"}),
                        "called": False,
                    },
                }
            ),
            ToolState(
                {
                    "baz": {
                        "tool": ToolCall({"name": "baz", "args": {"param": "value"}, "id": "789", "type": "tool_call"}),
                        "called": False,
                    }
                }
            ),
            ToolState(
                {
                    "foo": {"tool": ToolCall({"name": "foo", "args": {"a": 1, "b": 2}, "id": "123"}), "called": False},
                    "bar": {
                        "tool": ToolCall({"name": "bar", "args": {"x": 10, "y": 20}, "id": "456"}),
                        "called": False,
                    },
                    "baz": {
                        "tool": ToolCall({"name": "baz", "args": {"param": "value"}, "id": "789", "type": "tool_call"}),
                        "called": False,
                    },
                }
            ),
        ),
        (
            ToolState(
                {
                    "foo": {"tool": ToolCall({"name": "foo", "args": {"a": 1, "b": 2}, "id": "123"}), "called": False},
                    "bar": {
                        "tool": ToolCall({"name": "bar", "args": {"x": 10, "y": 20}, "id": "456"}),
                        "called": False,
                    },
                }
            ),
            ToolState({"bar": None}),
            ToolState(
                {"foo": {"tool": ToolCall({"name": "foo", "args": {"a": 1, "b": 2}, "id": "123"}), "called": False}}
            ),
        ),
        (
            ToolState(
                {"foo": {"tool": ToolCall({"name": "foo", "args": {"a": 1, "b": 2}, "id": "123"}), "called": False}}
            ),
            None,
            ToolState(),
        ),
        (
            ToolState(
                {"foo": {"tool": ToolCall({"name": "foo", "args": {"a": 1, "b": 2}, "id": "123"}), "called": False}}
            ),
            ToolState(
                {"foo": {"tool": ToolCall({"name": "foo", "args": {"a": 1, "b": 2}, "id": "123"}), "called": True}}
            ),
            ToolState(
                {"foo": {"tool": ToolCall({"name": "foo", "args": {"a": 1, "b": 2}, "id": "123"}), "called": True}}
            ),
        ),
    ],
)
def test_tool_calls_reducer(a: ToolState, b: ToolState, expected: ToolState):
    """Checks the key properties of the ToolState reducer.

    * If a new key is added, adds it to the state.
    * If an existing key is None'd, removes it
    * If update is None, clears all tool calls
    """
    result = tool_calls_reducer(a, b)
    assert result == expected, f"Expected: {expected}. Result: {result}"


TEST_QUERY = RedboxQuery(
    question="Lorem ipsum?",
    s3_keys=["s3_key.txt"],
    user_uuid=uuid4(),
    chat_history=[],
    ai_settings=AISettings(rag_k=3),
)


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        (
            RedboxState(
                request=TEST_QUERY,
                documents={
                    "group_1": {
                        "chunk_1": {"page_content": "foo", "metadata": {"index": 1, "file_name": "foo"}},
                        "chunk_2": {"page_content": "foo", "metadata": {"index": 1, "file_name": "foo"}},
                    },
                    "group_2": {"chunk_1": {"page_content": "foo", "metadata": {"index": 1, "file_name": "foo"}}},
                },
                text="Some old text",
                route_name="my_route",
                tool_calls={
                    "tool_1": {"tool": {"name": "foo", "args": {"a": 1, "b": 2}}, "called": False},
                    "tool_2": {"tool": {"name": "bar", "args": {"a": 1, "b": 2}}, "called": True},
                },
                metadata=RequestMetadata(
                    llm_calls=[
                        {
                            "id": "e7b9c8e4-8c6d-4f9b-8b8e-2f8e8e8e8e8e",
                            "llm_model_name": "gpt-4o",
                            "input_tokens": 80,
                            "output_tokens": 160,
                            "timestamp": datetime(2023, 10, 1, 12, 0, 0, tzinfo=timezone.utc).timestamp(),
                        },
                        {
                            "id": "d3b9c8e4-8c6d-4f9b-8b8e-2f8e8e8e8e8e",
                            "llm_model_name": "gpt-3.5",
                            "input_tokens": 60,
                            "output_tokens": 120,
                            "timestamp": datetime(2023, 10, 2, 14, 30, 0, tzinfo=timezone.utc).timestamp(),
                        },
                    ]
                ),
            ),
            RedboxState(
                request=TEST_QUERY,
                documents={
                    "group_1": {
                        "chunk_2": None,
                    },
                    "group_2": None,
                    "group_3": {
                        "chunk_1": {"page_content": "foo", "metadata": {"index": 1, "file_name": "foo"}},
                    },
                },
                text="Some new text",
                tool_calls={
                    "tool_1": {"called": True},
                    "tool_2": None,
                    "tool_3": {"tool": {"name": "foo", "args": {"a": 1, "b": 2}}, "called": False},
                },
                metadata=RequestMetadata(
                    llm_calls=[
                        {
                            "id": "c1b9c8e4-8c6d-4f9b-8b8e-2f8e8e8e8e8e",
                            "llm_model_name": "gpt-4o",
                            "input_tokens": 10,
                            "output_tokens": 10,
                            "timestamp": datetime(2023, 10, 3, 16, 45, 0, tzinfo=timezone.utc).timestamp(),
                        },
                    ]
                ),
            ),
            RedboxState(
                request=TEST_QUERY,
                documents={
                    "group_1": {
                        "chunk_1": {"page_content": "foo", "metadata": {"index": 1, "file_name": "foo"}},
                        "chunk_2": None,
                    },
                    "group_2": None,
                    "group_3": {
                        "chunk_1": {"page_content": "foo", "metadata": {"index": 1, "file_name": "foo"}},
                    },
                },
                text="Some new text",
                route_name="my_route",
                tool_calls={
                    "tool_1": {"tool": {"name": "foo", "args": {"a": 1, "b": 2}}, "called": True},
                    "tool_2": None,
                    "tool_3": {"tool": {"name": "foo", "args": {"a": 1, "b": 2}}, "called": False},
                },
                metadata=RequestMetadata(
                    llm_calls=[
                        {
                            "id": "e7b9c8e4-8c6d-4f9b-8b8e-2f8e8e8e8e8e",
                            "llm_model_name": "gpt-4o",
                            "input_tokens": 80,
                            "output_tokens": 160,
                            "timestamp": datetime(2023, 10, 1, 12, 0, 0, tzinfo=timezone.utc).timestamp(),
                        },
                        {
                            "id": "d3b9c8e4-8c6d-4f9b-8b8e-2f8e8e8e8e8e",
                            "llm_model_name": "gpt-3.5",
                            "input_tokens": 60,
                            "output_tokens": 120,
                            "timestamp": datetime(2023, 10, 2, 14, 30, 0, tzinfo=timezone.utc).timestamp(),
                        },
                        {
                            "id": "c1b9c8e4-8c6d-4f9b-8b8e-2f8e8e8e8e8e",
                            "llm_model_name": "gpt-4o",
                            "input_tokens": 10,
                            "output_tokens": 10,
                            "timestamp": datetime(2023, 10, 3, 16, 45, 0, tzinfo=timezone.utc).timestamp(),
                        },
                    ]
                ),
            ),
        ),
    ],
)
def test_merge_redbox_state_updates(a: RedboxState, b: RedboxState, expected: RedboxState):
    """
    Checks that state updates will be merged correctly.

    In the above data, a second update contradicts the first in the following ways:

    * A document group is None'd
    * A documment group is added
    * A documment group chunk is None'd
    * A static field (text) is set with something different
    * A static field (route) isn't included in the update
    * A tool call is modified to show as called
    * A tool call is None'd
    * A tool call is added
    * A new llm_call is added to the metadata
    """
    result = merge_redbox_state_updates(a, b)
    assert result == expected, f"Expected: {expected}. Result: {result}"
