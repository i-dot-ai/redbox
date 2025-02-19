import json
import logging
import os
from asyncio import CancelledError
from collections.abc import Sequence
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.db.models import Model
from django.forms import model_to_dict
from langchain_core.documents import Document
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage
from pydantic import BaseModel
from websockets import WebSocketClientProtocol
from websockets.legacy.client import Connect

from redbox.models.chain import (
    RedboxState,
)
from redbox_app.redbox_core import error_messages
from redbox_app.redbox_core.consumers import ChatConsumer
from redbox_app.redbox_core.models import (
    Chat,
    ChatMessage,
    File,
)

User = get_user_model()

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio()
async def test_chat_consumer_with_new_session(chat: Chat, mocked_connect: Connect):
    # Given

    # When
    with patch("redbox_app.redbox_core.consumers.ChatConsumer.redbox._get_runnable", new=lambda _: mocked_connect):
        communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), "/ws/chat/")
        communicator.scope["user"] = chat.user
        communicator.scope["url_route"] = {"kwargs": {"chat_id": chat.id}}
        connected, _ = await communicator.connect()
        assert connected

        await communicator.send_json_to({"message": "Hello Hal."})
        response_1 = await communicator.receive_json_from(timeout=5)
        response_2 = await communicator.receive_json_from(timeout=5)
        response_3 = await communicator.receive_json_from(timeout=5)
        response_4 = await communicator.receive_json_from(timeout=5)

        # Then
        assert response_1["type"] == "info"
        assert response_1["data"] == "Loading"
        assert response_2["type"] == "text"
        assert response_2["data"] == "Good afternoon, "
        assert response_3["type"] == "text"
        assert response_3["data"] == "Mr. Amor."
        assert response_4["type"] == "end"

        # Close
        await communicator.disconnect()

    assert await get_chat_message_text(chat.user, ChatMessage.Role.user) == ["Hello Hal."]
    assert await get_chat_message_text(chat.user, ChatMessage.Role.ai) == ["Good afternoon, Mr. Amor."]


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio()
async def test_chat_consumer_staff_user(staff_user: User, chat: Chat, mocked_connect: Connect):
    # Given

    # When
    with patch("redbox_app.redbox_core.consumers.ChatConsumer.redbox._get_runnable", new=lambda _: mocked_connect):
        communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), "/ws/chat/")
        communicator.scope["user"] = staff_user
        communicator.scope["url_route"] = {"kwargs": {"chat_id": chat.id}}
        connected, _ = await communicator.connect()
        assert connected

        await communicator.send_json_to({"message": "Hello Hal.", "output_text": "hello"})
        response_1 = await communicator.receive_json_from(timeout=5)
        response_2 = await communicator.receive_json_from(timeout=5)
        response_3 = await communicator.receive_json_from(timeout=5)
        response_4 = await communicator.receive_json_from(timeout=5)

        # Then
        assert response_1["type"] == "info"
        assert response_1["data"] == "Loading"
        assert response_2["type"] == "text"
        assert response_2["data"] == "Good afternoon, "
        assert response_3["type"] == "text"
        assert response_3["data"] == "Mr. Amor."
        assert response_4["type"] == "end"

        # Close
        await communicator.disconnect()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio()
async def test_chat_consumer_with_existing_session(chat: Chat, mocked_connect: Connect):
    # Given

    # When
    with patch("redbox_app.redbox_core.consumers.ChatConsumer.redbox._get_runnable", new=lambda _: mocked_connect):
        communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), "/ws/chat/")
        communicator.scope["user"] = chat.user
        communicator.scope["url_route"] = {"kwargs": {"chat_id": chat.id}}
        connected, _ = await communicator.connect()
        assert connected

        await communicator.send_json_to({"message": "Hello Hal."})

        # Close
        await communicator.disconnect()

    assert await get_chat_message_text(chat.user, ChatMessage.Role.user) == ["Hello Hal."]
    assert await get_chat_message_text(chat.user, ChatMessage.Role.ai) == ["Good afternoon, Mr. Amor."]


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio()
async def test_chat_consumer_with_naughty_question(chat: Chat, mocked_connect: Connect):
    # Given

    # When
    with patch("redbox_app.redbox_core.consumers.ChatConsumer.redbox._get_runnable", new=lambda _: mocked_connect):
        communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), "/ws/chat/")
        communicator.scope["user"] = chat.user
        communicator.scope["url_route"] = {"kwargs": {"chat_id": chat.id}}
        connected, _ = await communicator.connect()
        assert connected

        await communicator.send_json_to({"message": "Hello Hal. \x00"})
        response_1 = await communicator.receive_json_from(timeout=5)
        response_2 = await communicator.receive_json_from(timeout=5)
        response_3 = await communicator.receive_json_from(timeout=5)
        response_4 = await communicator.receive_json_from(timeout=5)

        # Then
        assert response_1["type"] == "info"
        assert response_1["data"] == "Loading"
        assert response_2["type"] == "text"
        assert response_2["data"] == "Good afternoon, "
        assert response_3["type"] == "text"
        assert response_3["data"] == "Mr. Amor."
        assert response_4["type"] == "end"

        # Close
        await communicator.disconnect()

    assert await get_chat_message_text(chat.user, ChatMessage.Role.user) == ["Hello Hal. \ufffd"]
    assert await get_chat_message_text(chat.user, ChatMessage.Role.ai) == ["Good afternoon, Mr. Amor."]


@database_sync_to_async
def get_chat_message_text(user: User, role: ChatMessage.Role) -> Sequence[str]:
    return [m.text for m in ChatMessage.objects.filter(chat__user=user, role=role)]


@pytest.mark.xfail()
@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio()
async def test_chat_consumer_with_selected_files(
    several_files: Sequence[File],
    chat_with_files: Chat,
    mocked_connect_with_several_files: Connect,
    llm_backend,
):
    # Given
    selected_files: Sequence[File] = several_files[2:]

    # When
    with patch(
        "redbox_app.redbox_core.consumers.ChatConsumer.redbox._get_runnable",
        new=lambda _: mocked_connect_with_several_files,
    ):
        communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), "/ws/chat/")
        communicator.scope["user"] = chat_with_files.user
        communicator.scope["url_route"] = {"kwargs": {"chat_id": chat_with_files.id}}
        connected, _ = await communicator.connect()
        assert connected

        await communicator.send_json_to(
            {
                "message": "Third question, with selected files?",
            }
        )

        # Close
        await communicator.disconnect()

    # Then

    # TODO (@brunns): Assert selected files sent to core.
    # Requires fix for https://github.com/django/channels/issues/1091
    # fixed now merged in https://github.com/django/channels/pull/2101, but not released
    # Retry this when a version of Channels after 4.1.0 is released
    mocked_websocket = mocked_connect_with_several_files.return_value.__aenter__.return_value
    expected = json.dumps(
        {
            "message_history": [
                {"role": "user", "text": "A question?"},
                {"role": "ai", "text": "An answer."},
                {"role": "user", "text": "A second question?"},
                {"role": "ai", "text": "A second answer."},
                {"role": "user", "text": "Third question, with selected files?"},
            ],
            "selected_files": [str(x.id) for x in selected_files],
            "chat_backend": llm_backend,
        }
    )
    mocked_websocket.send.assert_called_with(expected)

    # TODO (@brunns): Assert selected files saved to model.
    # Requires fix for https://github.com/django/channels/issues/1091
    all_messages = get_chat_messages(chat_with_files.user)
    last_user_message = [m for m in all_messages if m.rule == ChatMessage.Role.user][-1]
    assert last_user_message.selected_files == selected_files


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio()
async def test_chat_consumer_with_connection_error(chat: Chat, mocked_breaking_connect: Connect):
    # Given

    # When
    with patch(
        "redbox_app.redbox_core.consumers.ChatConsumer.redbox._get_runnable", new=lambda _: mocked_breaking_connect
    ):
        communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), "/ws/chat/")
        communicator.scope["user"] = chat.user
        communicator.scope["url_route"] = {"kwargs": {"chat_id": chat.id}}
        connected, _ = await communicator.connect()
        assert connected

        await communicator.send_json_to({"message": "Hello Hal."})
        response_1 = await communicator.receive_json_from(timeout=5)
        response_2 = await communicator.receive_json_from(timeout=5)

        # Then
        assert response_1["type"] == "info"
        assert response_1["data"] == "Loading"
        assert response_2["type"] == "error"


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio()
async def test_chat_consumer_with_explicit_unhandled_error(
    chat: Chat, mocked_connect_with_explicit_unhandled_error: Connect
):
    # Given

    # When
    with patch(
        "redbox_app.redbox_core.consumers.ChatConsumer.redbox._get_runnable",
        new=lambda _: mocked_connect_with_explicit_unhandled_error,
    ):
        communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), "/ws/chat/")
        communicator.scope["user"] = chat.user
        communicator.scope["url_route"] = {"kwargs": {"chat_id": chat.id}}
        connected, _ = await communicator.connect()
        assert connected

        await communicator.send_json_to({"message": "Hello Hal."})
        response_1 = await communicator.receive_json_from(timeout=5)
        response_2 = await communicator.receive_json_from(timeout=5)
        response_3 = await communicator.receive_json_from(timeout=5)

        # Then
        assert response_1["type"] == "info"
        assert response_1["data"] == "Loading"
        assert response_2["type"] == "text"
        assert response_2["data"] == "Good afternoon, "
        assert response_3["type"] == "text"
        assert response_3["data"] == error_messages.CORE_ERROR_MESSAGE

        # Close
        await communicator.disconnect()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio()
async def test_chat_consumer_with_rate_limited_error(chat: Chat, mocked_connect_with_rate_limited_error: Connect):
    # Given

    # When
    with patch(
        "redbox_app.redbox_core.consumers.ChatConsumer.redbox._get_runnable",
        new=lambda _: mocked_connect_with_rate_limited_error,
    ):
        communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), "/ws/chat/")
        communicator.scope["user"] = chat.user
        communicator.scope["url_route"] = {"kwargs": {"chat_id": chat.id}}
        connected, _ = await communicator.connect()
        assert connected

        await communicator.send_json_to({"message": "Hello Hal."})
        response_1 = await communicator.receive_json_from(timeout=5)
        response_2 = await communicator.receive_json_from(timeout=5)
        response_3 = await communicator.receive_json_from(timeout=5)

        # Then
        assert response_1["type"] == "info"
        assert response_1["data"] == "Loading"
        assert response_2["type"] == "text"
        assert response_2["data"] == "Good afternoon, "
        assert response_3["type"] == "text"
        assert response_3["data"] == error_messages.RATE_LIMITED
        # Close
        await communicator.disconnect()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio()
async def test_chat_consumer_with_explicit_no_document_selected_error(
    chat: Chat, mocked_connect_with_explicit_no_document_selected_error: Connect
):
    # Given

    # When
    with patch(
        "redbox_app.redbox_core.consumers.ChatConsumer.redbox._get_runnable",
        new=lambda _: mocked_connect_with_explicit_no_document_selected_error,
    ):
        communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), "/ws/chat/")
        communicator.scope["user"] = chat.user
        communicator.scope["url_route"] = {"kwargs": {"chat_id": chat.id}}
        connected, _ = await communicator.connect()
        assert connected

        await communicator.send_json_to({"message": "Hello Hal."})
        response_1 = await communicator.receive_json_from(timeout=5)
        response_2 = await communicator.receive_json_from(timeout=5)

        # Then
        assert response_1["type"] == "info"
        assert response_1["data"] == "Loading"
        assert response_2["data"] == error_messages.SELECT_DOCUMENT
        # Close
        await communicator.disconnect()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio()
async def test_chat_consumer_redbox_state(
    several_files: Sequence[File], chat_with_files: Chat, mocked_connect_with_several_files: Connect, llm_backend
):
    # Given

    # When
    with (
        patch(
            "redbox_app.redbox_core.consumers.ChatConsumer.redbox._get_runnable",
            new=lambda _: mocked_connect_with_several_files,
        ),
        patch("redbox_app.redbox_core.consumers.ChatConsumer.redbox.run") as mock_run,
    ):
        communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), "/ws/chat/")
        communicator.scope["user"] = chat_with_files.user
        communicator.scope["url_route"] = {"kwargs": {"chat_id": chat_with_files.id}}
        connected, _ = await communicator.connect()
        assert connected

        await communicator.send_json_to({"message": "Third question, with selected files?"})

        # Close
        await communicator.disconnect()

        chat_backend_dict = model_to_dict(llm_backend)

        # Then
        expected_request = RedboxState(
            documents=[
                Document(page_content=str(f.text), metadata={"uri": f.original_file.name}) for f in several_files
            ],
            messages=[
                HumanMessage(content="A question?"),
                AIMessage(content="An answer."),
                HumanMessage(content="A second question?"),
                AIMessage(content="A second answer."),
                HumanMessage(content="Third question, with selected files?"),
            ],
            chat_backend=chat_backend_dict,
        )
        redbox_state = mock_run.call_args.args[0]  # pulls out the args that redbox.run was called with

        assert redbox_state == expected_request, f"Expected {expected_request}. Received: {redbox_state}"


@database_sync_to_async
def get_chat_messages(user: User) -> Sequence[ChatMessage]:
    return list(
        ChatMessage.objects.filter(chat__user=user)
        .order_by("created_at")
        .prefetch_related("chat")
        .prefetch_related("source_files")
        .prefetch_related("selected_files")
    )


class Token(BaseModel):
    content: str


class CannedGraphLLM(BaseChatModel):
    responses: list[dict]

    def _generate(self, *_args, **_kwargs):
        for _ in self.responses:
            yield

    def _llm_type(self):
        return "canned"

    async def astream_events(self, *_args, **_kwargs):
        for response in self.responses:
            yield response


@pytest.fixture()
def mocked_connect() -> Connect:
    responses = [
        {
            "event": "on_chat_model_stream",
            "data": {"chunk": Token(content="Good afternoon, ")},
        },
        {"event": "on_chat_model_stream", "data": {"chunk": Token(content="Mr. Amor.")}},
        {
            "event": "on_chain_end",
            "data": {"output": AIMessageChunk(content="Good afternoon, Mr. Amor.")},
        },
    ]

    return CannedGraphLLM(responses=responses)


@pytest.fixture()
def mocked_connect_with_naughty_citation() -> CannedGraphLLM:
    responses = [
        {
            "event": "on_chat_model_stream",
            "data": {"chunk": Token(content="Good afternoon, Mr. Amor.")},
        },
        {
            "event": "on_chain_end",
            "data": {"output": AIMessageChunk(content="Good afternoon, Mr. Amor.")},
        },
    ]

    return CannedGraphLLM(responses=responses)


@pytest.fixture()
def mocked_breaking_connect() -> Connect:
    mocked_graph = MagicMock(name="mocked_graph")
    mocked_graph.astream_events.side_effect = CancelledError()
    return mocked_graph


@pytest.fixture()
def mocked_connect_with_explicit_unhandled_error() -> CannedGraphLLM:
    responses = [
        {
            "event": "on_chat_model_stream",
            "data": {"chunk": Token(content="Good afternoon, ")},
        },
        {
            "event": "on_chat_model_stream",
            "data": {"chunk": Token(content=error_messages.CORE_ERROR_MESSAGE)},
        },
    ]

    return CannedGraphLLM(responses=responses)


@pytest.fixture()
def mocked_connect_with_rate_limited_error() -> CannedGraphLLM:
    responses = [
        {
            "event": "on_chat_model_stream",
            "data": {"chunk": Token(content="Good afternoon, ")},
        },
        {
            "event": "on_chat_model_stream",
            "data": {"chunk": Token(content=error_messages.RATE_LIMITED)},
        },
    ]

    return CannedGraphLLM(responses=responses)


@pytest.fixture()
def mocked_connect_with_explicit_no_document_selected_error() -> CannedGraphLLM:
    responses = [
        {
            "event": "on_chat_model_stream",
            "data": {"chunk": Token(content=error_messages.SELECT_DOCUMENT)},
        },
    ]

    return CannedGraphLLM(responses=responses)


@pytest.fixture()
def mocked_connect_with_several_files(several_files: Sequence[File]) -> Connect:
    mocked_websocket = AsyncMock(spec=WebSocketClientProtocol, name="mocked_websocket")
    mocked_connect = MagicMock(spec=Connect, name="mocked_connect")
    mocked_connect.return_value.__aenter__.return_value = mocked_websocket
    mocked_websocket.__aiter__.return_value = [
        json.dumps({"resource_type": "text", "data": "Third "}),
        json.dumps({"resource_type": "text", "data": "answer."}),
        json.dumps(
            {
                "resource_type": "documents",
                "data": [{"s3_key": f.file_name, "page_content": "a secret forth answer"} for f in several_files[2:]],
            }
        ),
        json.dumps({"resource_type": "end"}),
    ]
    return mocked_connect


@database_sync_to_async
def refresh_from_db(obj: Model) -> None:
    obj.refresh_from_db()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio()
async def test_chat_consumer_with_context_window_error(large_file: File):
    # Given large_file

    # When
    communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), "/ws/chat/")
    communicator.scope["user"] = large_file.chat.user
    communicator.scope["url_route"] = {"kwargs": {"chat_id": large_file.chat.id}}
    connected, _ = await communicator.connect()
    assert connected

    await communicator.send_json_to({"message": "Hello Hal."})
    response_1 = await communicator.receive_json_from(timeout=5)

    # Then
    assert response_1["type"] == "error"
    assert response_1["data"] == error_messages.FILES_TOO_LARGE
    # Close
    await communicator.disconnect()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio()
async def test_chat_consumer_with_context_window_error_with_suggestion(large_file: File, big_llm_backend):
    # Given large_file

    # When
    communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), "/ws/chat/")
    communicator.scope["user"] = large_file.chat.user
    communicator.scope["url_route"] = {"kwargs": {"chat_id": large_file.chat.id}}
    connected, _ = await communicator.connect()
    assert connected

    await communicator.send_json_to({"message": "Hello Hal."})
    response_1 = await communicator.receive_json_from(timeout=5)

    # Then
    assert response_1["type"] == "error"
    assert response_1["data"].startswith(error_messages.FILES_TOO_LARGE)
    assert response_1["data"].endswith(f"`{big_llm_backend}`: {big_llm_backend.context_window_size} tokens")

    # Close
    await communicator.disconnect()
