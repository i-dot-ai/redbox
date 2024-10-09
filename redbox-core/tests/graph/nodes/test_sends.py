from uuid import uuid4

from langchain_core.documents import Document
from langgraph.constants import Send

from redbox.graph.nodes.sends import build_document_group_send, build_document_chunk_send
from redbox.models.chain import RedboxState, RedboxQuery, DocumentState


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
