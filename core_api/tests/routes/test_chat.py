import json
from http import HTTPStatus
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompt_values import ChatPromptValue
from langchain_core.runnables import Runnable
from langchain_core.runnables.schema import StreamEvent
from starlette.websockets import WebSocketDisconnect

if TYPE_CHECKING:
    from collections.abc import Iterable

system_chat = {"text": "test", "role": "system"}
user_chat = {"text": "test", "role": "user"}

test_history = [
    ([system_chat], 422),
    ([user_chat, system_chat], 422),
    ([system_chat, system_chat], 422),
    # ([system_chat, user_chat], 200), TODO: restore this test
]


def mock_chat_prompt():
    return ChatPromptValue(
        messages=[
            SystemMessage(content="You are a helpful AI bot."),
            HumanMessage(content="Hello, how are you doing?"),
        ]
    )


class MockChain:
    @staticmethod
    def stream():
        yield [{"input": "Test input", "text": "Test output"}]


def mock_get_chain():
    return MockChain()


@pytest.mark.parametrize(("chat_history", "status_code"), test_history)
def test_simple_chat(chat_history, status_code, app_client, monkeypatch, headers):
    monkeypatch.setattr("langchain_core.prompts.ChatPromptTemplate.from_messages", mock_chat_prompt)
    monkeypatch.setattr("core_api.src.routes.chat.LLMChain", mock_get_chain)

    response = app_client.post("/chat/vanilla", json={"message_history": chat_history}, headers=headers)
    assert response.status_code == status_code


def test_rag_chat_streamed(app_client, headers):
    # Given
    message_history = [
        {"text": "What can I do for you?", "role": "system"},
        {"text": "Who put the ram in the rama lama ding dong?", "role": "user"},
    ]
    events: Iterable[StreamEvent] = [
        StreamEvent(
            event="on_chat_model_stream",
            name="event-1",
            data={
                "chunk": SimpleNamespace(
                    content="Who Put the Bomp (in the Bomp, Bomp, Bomp) is a doo-wop style novelty song from 1961 "
                )
            },
            run_id="run_id",
        ),
        StreamEvent(
            event="on_chat_model_stream",
            name="event-2",
            data={"chunk": SimpleNamespace(content="by the American songwriter Barry Mann.")},
            run_id="run_id",
        ),
    ]

    build_retrieval_chain = mock_build_retrieval_chain(events)

    with (
        patch("core_api.src.routes.chat.build_retrieval_chain", new=build_retrieval_chain),
        app_client.websocket_connect("/chat/rag", headers=headers) as websocket,
    ):
        # When
        websocket.send_text(json.dumps({"message_history": message_history}))

        all_text, docs = [], []
        while True:
            try:
                actual = websocket.receive_json()
                if actual["resource_type"] == "text":
                    all_text.append(actual["data"])
                if actual["resource_type"] == "documents":
                    docs.append(actual["data"])
            except WebSocketDisconnect:
                break

        # Then
        text = "".join(all_text)
        assert "Barry Mann" in text


def mock_build_retrieval_chain(events):
    event_iterable = MagicMock(name="event_iterable")
    event_iterable.__aiter__.return_value = events

    astream_events = MagicMock(name="astream_events", return_value=event_iterable)

    retrieval_chain = AsyncMock(spec=Runnable, name="retrieval_chain")
    retrieval_chain.astream_events = astream_events

    return AsyncMock(name="build_retrieval_chain", return_value=(retrieval_chain, None))


@pytest.mark.parametrize(
    ("payload", "error"),
    [
        (
            [{"text": "hello", "role": "system"}],
            {"detail": "Chat history should include both system and user prompts"},
        ),
        (
            [{"text": "hello", "role": "user"}, {"text": "hello", "role": "user"}],
            {"detail": "The first entry in the chat history should be a system prompt"},
        ),
        (
            [{"text": "hello", "role": "system"}, {"text": "hello", "role": "system"}],
            {"detail": "The final entry in the chat history should be a user question"},
        ),
    ],
)
def test_chat_errors(app_client, payload, error, headers):
    """Given the app is running
    When I POST a malformed payload to /chat/vanilla
    I expect a 422 error and a meaningful message
    """
    response = app_client.post("/chat/vanilla", json={"message_history": payload}, headers=headers)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.json() == error
