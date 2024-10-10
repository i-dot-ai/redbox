from uuid import uuid4

from langchain_core.documents import Document
from langchain_core.messages import ToolCall
from langgraph.constants import Send

from redbox.graph.nodes.sends import build_document_chunk_send, build_document_group_send, build_tool_send
from redbox.models.chain import DocumentState, RedboxQuery, RedboxState, ToolState


def test_build_document_group_send():
    target = "my-target"
    request = RedboxQuery(question="what colour is the sky?", user_uuid=uuid4(), chat_history=[])
    documents = DocumentState(
        group={uuid4(): Document(page_content="Hello, world!"), uuid4(): Document(page_content="Goodbye, world!")}
    )

    document_group_send = build_document_group_send("my-target")
    state = RedboxState(
        request=request,
        documents=documents,
        text=None,
        route_name=None,
    )
    actual = document_group_send(state)
    expected = [Send(node=target, arg=state)]
    assert expected == actual


def test_build_document_chunk_send():
    target = "my-target"
    request = RedboxQuery(question="what colour is the sky?", user_uuid=uuid4(), chat_history=[])

    uuid_1 = uuid4()
    doc_1 = Document(page_content="Hello, world!")
    uuid_2 = uuid4()
    doc_2 = Document(page_content="Goodbye, world!")

    document_chunk_send = build_document_chunk_send("my-target")
    state = RedboxState(
        request=request,
        documents=DocumentState(group={uuid_1: doc_1, uuid_2: doc_2}),
        text=None,
        route_name=None,
    )
    actual = document_chunk_send(state)
    expected = [
        Send(
            node=target,
            arg=RedboxState(
                request=request,
                documents=DocumentState(group={uuid_1: doc_1}),
                text=None,
                route_name=None,
            ),
        ),
        Send(
            node=target,
            arg=RedboxState(
                request=request,
                documents=DocumentState(group={uuid_2: doc_2}),
                text=None,
                route_name=None,
            ),
        ),
    ]
    assert expected == actual


def test_build_tool_send():
    target = "my-target"
    request = RedboxQuery(question="what colour is the sky?", user_uuid=uuid4(), chat_history=[])

    tool_call_1 = {
        "foo": {"tool": ToolCall({"name": "foo", "args": {"a": 1, "b": 2}, "id": "123"}), "called": False},
    }
    tool_call_2 = {
        "bar": {
            "tool": ToolCall({"name": "bar", "args": {"x": 10, "y": 20}, "id": "456"}),
            "called": False,
        },
    }

    tool_send = build_tool_send("my-target")
    actual = tool_send(
        RedboxState(
            request=request,
            tool_calls=ToolState(tool_call_1 | tool_call_2),
            text=None,
            route_name=None,
        ),
    )
    expected = [
        Send(
            node=target,
            arg=RedboxState(
                request=request,
                tool_calls=ToolState(tool_call_1),
                text=None,
                route_name=None,
            ),
        ),
        Send(
            node=target,
            arg=RedboxState(
                request=request,
                tool_calls=ToolState(tool_call_2),
                text=None,
                route_name=None,
            ),
        ),
    ]
    assert expected == actual
