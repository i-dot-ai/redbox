import json
import logging
import os
from asyncio import CancelledError
from collections.abc import Sequence
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.db.models import Model
from langchain_core.documents import Document
from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel
from websockets import WebSocketClientProtocol
from websockets.legacy.client import Connect

from redbox.models.chain import LLMCallMetadata, RedboxQuery, RequestMetadata
from redbox.models.graph import FINAL_RESPONSE_TAG, ROUTE_NAME_TAG, SOURCE_DOCUMENTS_TAG, RedboxActivityEvent
from redbox.models.prompts import CHAT_MAP_QUESTION_PROMPT
from redbox_app.redbox_core import error_messages
from redbox_app.redbox_core.consumers import ChatConsumer
from redbox_app.redbox_core.models import (
    ActivityEvent,
    Chat,
    ChatMessage,
    ChatMessageTokenUse,
    File,
)

User = get_user_model()

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


@database_sync_to_async
def get_token_use_model(use_type: str) -> str:
    return ChatMessageTokenUse.objects.filter(use_type=use_type).latest("created_at").model_name


@database_sync_to_async
def get_activity_model() -> str:
    return ActivityEvent.objects.latest("created_at").message


@database_sync_to_async
def get_token_use_count(use_type: str) -> int:
    return ChatMessageTokenUse.objects.filter(use_type=use_type).latest("created_at").token_count


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio()
async def test_chat_consumer_with_new_session(alice: User, uploaded_file: File, mocked_connect: Connect):
    # Given

    # When
    with patch("redbox_app.redbox_core.consumers.ChatConsumer.redbox.graph", new=mocked_connect):
        communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), "/ws/chat/")
        communicator.scope["user"] = alice
        connected, _ = await communicator.connect()
        assert connected

        await communicator.send_json_to({"message": "Hello Hal."})
        response1 = await communicator.receive_json_from(timeout=5)
        response2 = await communicator.receive_json_from(timeout=5)
        response3 = await communicator.receive_json_from(timeout=5)
        response4 = await communicator.receive_json_from(timeout=5)
        response5 = await communicator.receive_json_from(timeout=5)

        # Then
        assert response1["type"] == "session-id"
        assert response2["type"] == "text"
        assert response2["data"] == "Good afternoon, "
        assert response3["type"] == "text"
        assert response3["data"] == "Mr. Amor."
        assert response4["type"] == "route"
        assert response4["data"] == "gratitude"
        assert response5["type"] == "source"
        assert response5["data"]["file_name"] == uploaded_file.file_name
        # Close
        await communicator.disconnect()

    assert await get_chat_message_text(alice, ChatMessage.Role.user) == ["Hello Hal."]
    assert await get_chat_message_text(alice, ChatMessage.Role.ai) == ["Good afternoon, Mr. Amor."]
    assert await get_chat_message_route(alice, ChatMessage.Role.ai) == ["gratitude"]

    expected_citations = {("Good afternoon Mr Amor", ()), ("Good afternoon Mr Amor", (34, 35))}
    assert await get_chat_message_citation_set(alice, ChatMessage.Role.ai) == expected_citations
    await refresh_from_db(uploaded_file)
    assert uploaded_file.last_referenced.date() == datetime.now(tz=UTC).date()

    assert await get_token_use_model(ChatMessageTokenUse.UseType.INPUT) == "gpt-4o"
    assert await get_token_use_model(ChatMessageTokenUse.UseType.OUTPUT) == "gpt-4o"
    assert await get_token_use_count(ChatMessageTokenUse.UseType.INPUT) == 123
    assert await get_token_use_count(ChatMessageTokenUse.UseType.OUTPUT) == 1000
    assert await get_activity_model() == "fish and chips"


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio()
async def test_chat_consumer_staff_user(staff_user: User, mocked_connect: Connect):
    # Given

    # When
    with patch("redbox_app.redbox_core.consumers.ChatConsumer.redbox.graph", new=mocked_connect):
        communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), "/ws/chat/")
        communicator.scope["user"] = staff_user
        connected, _ = await communicator.connect()
        assert connected

        await communicator.send_json_to({"message": "Hello Hal.", "output_text": "hello"})
        response1 = await communicator.receive_json_from(timeout=5)
        response2 = await communicator.receive_json_from(timeout=5)
        response3 = await communicator.receive_json_from(timeout=5)
        response4 = await communicator.receive_json_from(timeout=5)
        _response5 = await communicator.receive_json_from(timeout=5)

        # Then
        assert response1["type"] == "session-id"
        assert response2["type"] == "text"
        assert response2["data"] == "Good afternoon, "
        assert response3["type"] == "text"
        assert response3["data"] == "Mr. Amor."
        assert response4["type"] == "route"
        assert response4["data"] == "gratitude"
        # Close
        await communicator.disconnect()

    assert await get_chat_message_route(staff_user, ChatMessage.Role.ai) == ["gratitude"]


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio()
async def test_chat_consumer_with_existing_session(alice: User, chat: Chat, mocked_connect: Connect):
    # Given

    # When
    with patch("redbox_app.redbox_core.consumers.ChatConsumer.redbox.graph", new=mocked_connect):
        communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), "/ws/chat/")
        communicator.scope["user"] = alice
        connected, _ = await communicator.connect()
        assert connected

        await communicator.send_json_to({"message": "Hello Hal.", "sessionId": str(chat.id)})
        response1 = await communicator.receive_json_from(timeout=5)

        # Then
        assert response1["type"] == "session-id"
        assert response1["data"] == str(chat.id)

        # Close
        await communicator.disconnect()

    assert await get_chat_message_text(alice, ChatMessage.Role.user) == ["Hello Hal."]
    assert await get_chat_message_text(alice, ChatMessage.Role.ai) == ["Good afternoon, Mr. Amor."]


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio()
async def test_chat_consumer_with_naughty_question(alice: User, uploaded_file: File, mocked_connect: Connect):
    # Given

    # When
    with patch("redbox_app.redbox_core.consumers.ChatConsumer.redbox.graph", new=mocked_connect):
        communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), "/ws/chat/")
        communicator.scope["user"] = alice
        connected, _ = await communicator.connect()
        assert connected

        await communicator.send_json_to({"message": "Hello Hal. \x00"})
        response1 = await communicator.receive_json_from(timeout=5)
        response2 = await communicator.receive_json_from(timeout=5)
        response3 = await communicator.receive_json_from(timeout=5)
        response4 = await communicator.receive_json_from(timeout=5)
        response5 = await communicator.receive_json_from(timeout=5)

        # Then
        assert response1["type"] == "session-id"
        assert response2["type"] == "text"
        assert response2["data"] == "Good afternoon, "
        assert response3["type"] == "text"
        assert response3["data"] == "Mr. Amor."
        assert response4["type"] == "route"
        assert response4["data"] == "gratitude"
        assert response5["type"] == "source"
        assert response5["data"]["file_name"] == uploaded_file.file_name
        # Close
        await communicator.disconnect()

    assert await get_chat_message_text(alice, ChatMessage.Role.user) == ["Hello Hal. \ufffd"]
    assert await get_chat_message_text(alice, ChatMessage.Role.ai) == ["Good afternoon, Mr. Amor."]
    assert await get_chat_message_route(alice, ChatMessage.Role.ai) == ["gratitude"]
    await refresh_from_db(uploaded_file)
    assert uploaded_file.last_referenced.date() == datetime.now(tz=UTC).date()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio()
async def test_chat_consumer_with_naughty_citation(
    alice: User, uploaded_file: File, mocked_connect_with_naughty_citation: Connect
):
    # Given

    # When
    with patch("redbox_app.redbox_core.consumers.ChatConsumer.redbox.graph", new=mocked_connect_with_naughty_citation):
        communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), "/ws/chat/")
        communicator.scope["user"] = alice
        connected, _ = await communicator.connect()
        assert connected

        await communicator.send_json_to({"message": "Hello Hal."})
        response1 = await communicator.receive_json_from(timeout=5)
        response2 = await communicator.receive_json_from(timeout=5)
        response3 = await communicator.receive_json_from(timeout=5)
        response4 = await communicator.receive_json_from(timeout=5)

        # Then
        assert response1["type"] == "session-id"
        assert response2["type"] == "text"
        assert response2["data"] == "Good afternoon, Mr. Amor."
        assert response3["type"] == "route"
        assert response3["data"] == "gratitude"
        assert response4["type"] == "source"
        assert response4["data"]["file_name"] == uploaded_file.file_name
        # Close
        await communicator.disconnect()

    assert await get_chat_message_text(alice, ChatMessage.Role.user) == ["Hello Hal."]
    assert await get_chat_message_text(alice, ChatMessage.Role.ai) == ["Good afternoon, Mr. Amor."]
    assert await get_chat_message_route(alice, ChatMessage.Role.ai) == ["gratitude"]
    await refresh_from_db(uploaded_file)
    assert uploaded_file.last_referenced.date() == datetime.now(tz=UTC).date()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio()
async def test_chat_consumer_agentic(alice: User, uploaded_file: File, mocked_connect_agentic_search: Connect):
    # Given

    # When
    with patch("redbox_app.redbox_core.consumers.ChatConsumer.redbox.graph", new=mocked_connect_agentic_search):
        communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), "/ws/chat/")
        communicator.scope["user"] = alice
        connected, _ = await communicator.connect()
        assert connected

        await communicator.send_json_to({"message": "Hello Hal."})
        response1 = await communicator.receive_json_from(timeout=5)
        response2 = await communicator.receive_json_from(timeout=5)
        response3 = await communicator.receive_json_from(timeout=5)
        response4 = await communicator.receive_json_from(timeout=5)
        response5 = await communicator.receive_json_from(timeout=5)

        # Then
        assert response1["type"] == "session-id"
        assert response2["type"] == "text"
        assert response2["data"] == "Good afternoon, "
        assert response3["type"] == "text"
        assert response3["data"] == "Mr. Amor."
        assert response4["type"] == "route"
        assert response4["data"] == "search/agentic"
        assert response5["type"] == "source"
        assert response5["data"]["file_name"] == uploaded_file.file_name
        # Close
        await communicator.disconnect()

    assert await get_chat_message_text(alice, ChatMessage.Role.user) == ["Hello Hal."]
    assert await get_chat_message_text(alice, ChatMessage.Role.ai) == ["Good afternoon, Mr. Amor."]

    expected_citations = {("Good afternoon Mr Amor", ()), ("Good afternoon Mr Amor", (34, 35))}
    assert await get_chat_message_citation_set(alice, ChatMessage.Role.ai) == expected_citations
    await refresh_from_db(uploaded_file)
    assert uploaded_file.last_referenced.date() == datetime.now(tz=UTC).date()

    assert await get_token_use_model(ChatMessageTokenUse.UseType.INPUT) == "gpt-4o"
    assert await get_token_use_model(ChatMessageTokenUse.UseType.OUTPUT) == "gpt-4o"
    assert await get_token_use_count(ChatMessageTokenUse.UseType.INPUT) == 123
    assert await get_token_use_count(ChatMessageTokenUse.UseType.OUTPUT) == 1000


@database_sync_to_async
def get_chat_message_text(user: User, role: ChatMessage.Role) -> Sequence[str]:
    return [m.text for m in ChatMessage.objects.filter(chat__user=user, role=role)]


@database_sync_to_async
def get_chat_message_citation_set(user: User, role: ChatMessage.Role) -> Sequence[tuple[str, tuple[int]]]:
    return {
        (citation.text, tuple(citation.page_numbers or []))
        for message in ChatMessage.objects.filter(chat__user=user, role=role)
        for source_file in message.source_files.all()
        for citation in source_file.citation_set.all()
    }


@database_sync_to_async
def get_chat_message_route(user: User, role: ChatMessage.Role) -> Sequence[str]:
    return [m.route for m in ChatMessage.objects.filter(chat__user=user, role=role)]


@pytest.mark.xfail()
@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio()
async def test_chat_consumer_with_selected_files(
    alice: User,
    several_files: Sequence[File],
    chat_with_files: Chat,
    mocked_connect_with_several_files: Connect,
):
    # Given
    selected_files: Sequence[File] = several_files[2:]

    # When
    with patch("redbox_app.redbox_core.consumers.ChatConsumer.redbox.graph", new=mocked_connect_with_several_files):
        communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), "/ws/chat/")
        communicator.scope["user"] = alice
        connected, _ = await communicator.connect()
        assert connected

        selected_file_core_uuids: Sequence[str] = [f.unique_name for f in selected_files]
        await communicator.send_json_to(
            {
                "message": "Third question, with selected files?",
                "sessionId": str(chat_with_files.id),
                "selectedFiles": selected_file_core_uuids,
            }
        )
        response1 = await communicator.receive_json_from(timeout=5)

        # Then
        assert response1["type"] == "session-id"
        assert response1["data"] == str(chat_with_files.id)

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
            "selected_files": selected_file_core_uuids,
            "ai_settings": await ChatConsumer.get_ai_settings(alice),
        }
    )
    mocked_websocket.send.assert_called_with(expected)

    # TODO (@brunns): Assert selected files saved to model.
    # Requires fix for https://github.com/django/channels/issues/1091
    all_messages = get_chat_messages(alice)
    last_user_message = [m for m in all_messages if m.rule == ChatMessage.Role.user][-1]
    assert last_user_message.selected_files == selected_files


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio()
async def test_chat_consumer_with_connection_error(alice: User, mocked_breaking_connect: Connect):
    # Given

    # When
    with patch("redbox_app.redbox_core.consumers.ChatConsumer.redbox.graph", new=mocked_breaking_connect):
        communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), "/ws/chat/")
        communicator.scope["user"] = alice
        connected, _ = await communicator.connect()
        assert connected

        await communicator.send_json_to({"message": "Hello Hal."})
        await communicator.receive_json_from(timeout=5)
        response2 = await communicator.receive_json_from(timeout=5)

        # Then
        assert response2["type"] == "error"


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio()
async def test_chat_consumer_with_explicit_unhandled_error(
    alice: User, mocked_connect_with_explicit_unhandled_error: Connect
):
    # Given

    # When
    with patch(
        "redbox_app.redbox_core.consumers.ChatConsumer.redbox.graph", new=mocked_connect_with_explicit_unhandled_error
    ):
        communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), "/ws/chat/")
        communicator.scope["user"] = alice
        connected, _ = await communicator.connect()
        assert connected

        await communicator.send_json_to({"message": "Hello Hal."})
        response1 = await communicator.receive_json_from(timeout=5)
        response2 = await communicator.receive_json_from(timeout=5)
        response3 = await communicator.receive_json_from(timeout=5)

        # Then
        assert response1["type"] == "session-id"
        assert response2["type"] == "text"
        assert response2["data"] == "Good afternoon, "
        assert response3["type"] == "text"
        assert response3["data"] == error_messages.CORE_ERROR_MESSAGE
        # Close
        await communicator.disconnect()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio()
async def test_chat_consumer_with_rate_limited_error(alice: User, mocked_connect_with_rate_limited_error: Connect):
    # Given

    # When
    with patch(
        "redbox_app.redbox_core.consumers.ChatConsumer.redbox.graph", new=mocked_connect_with_rate_limited_error
    ):
        communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), "/ws/chat/")
        communicator.scope["user"] = alice
        connected, _ = await communicator.connect()
        assert connected

        await communicator.send_json_to({"message": "Hello Hal."})
        response1 = await communicator.receive_json_from(timeout=5)
        response2 = await communicator.receive_json_from(timeout=5)
        response3 = await communicator.receive_json_from(timeout=5)

        # Then
        assert response1["type"] == "session-id"
        assert response2["type"] == "text"
        assert response2["data"] == "Good afternoon, "
        assert response3["type"] == "text"
        assert response3["data"] == error_messages.RATE_LIMITED
        # Close
        await communicator.disconnect()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio()
async def test_chat_consumer_with_explicit_no_document_selected_error(
    alice: User, mocked_connect_with_explicit_no_document_selected_error: Connect
):
    # Given

    # When
    with patch(
        "redbox_app.redbox_core.consumers.ChatConsumer.redbox.graph",
        new=mocked_connect_with_explicit_no_document_selected_error,
    ):
        communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), "/ws/chat/")
        communicator.scope["user"] = alice
        connected, _ = await communicator.connect()
        assert connected

        await communicator.send_json_to({"message": "Hello Hal."})
        response1 = await communicator.receive_json_from(timeout=5)
        response2 = await communicator.receive_json_from(timeout=5)

        # Then
        assert response1["type"] == "session-id"
        assert response2["type"] == "text"
        assert response2["data"] == error_messages.SELECT_DOCUMENT
        # Close
        await communicator.disconnect()


@pytest.mark.django_db()
@pytest.mark.asyncio()
async def test_chat_consumer_get_ai_settings(
    chat_with_alice: Chat, mocked_connect_with_explicit_no_document_selected_error: Connect
):
    with patch(
        "redbox_app.redbox_core.consumers.ChatConsumer.redbox.graph",
        new=mocked_connect_with_explicit_no_document_selected_error,
    ):
        communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), "/ws/chat/")
        communicator.scope["user"] = chat_with_alice.user
        connected, _ = await communicator.connect()
        assert connected

        ai_settings = await ChatConsumer.get_ai_settings(chat_with_alice)

        assert ai_settings.chat_map_question_prompt == CHAT_MAP_QUESTION_PROMPT
        assert ai_settings.chat_backend.name == chat_with_alice.chat_backend.name
        assert ai_settings.chat_backend.provider == chat_with_alice.chat_backend.provider
        assert not hasattr(ai_settings, "label")

        # Close
        await communicator.disconnect()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio()
async def test_chat_consumer_redbox_state(
    alice: User,
    several_files: Sequence[File],
    chat_with_files: Chat,
):
    # Given
    selected_files: Sequence[File] = several_files[2:]

    # When
    with patch("redbox_app.redbox_core.consumers.ChatConsumer.redbox.run") as mock_run:
        ai_settings = await ChatConsumer.get_ai_settings(chat_with_files)
        communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), "/ws/chat/")
        communicator.scope["user"] = alice
        connected, _ = await communicator.connect()
        assert connected

        selected_file_uuids: Sequence[str] = [str(f.id) for f in selected_files]
        selected_file_keys: Sequence[str] = [f.unique_name for f in selected_files]
        permitted_file_keys: Sequence[str] = [
            f.unique_name async for f in File.objects.filter(user=alice, status=File.Status.complete)
        ]
        assert selected_file_keys != permitted_file_keys

        await communicator.send_json_to(
            {
                "message": "Third question, with selected files?",
                "sessionId": str(chat_with_files.id),
                "selectedFiles": selected_file_uuids,
            }
        )
        response1 = await communicator.receive_json_from(timeout=5)

        # Then
        assert response1["type"] == "session-id"
        assert response1["data"] == str(chat_with_files.id)

        # Close
        await communicator.disconnect()

        # Then
        expected_request = RedboxQuery(
            question="Third question, with selected files?",
            s3_keys=selected_file_keys,
            user_uuid=alice.id,
            chat_history=[
                {"role": "user", "text": "A question?"},
                {"role": "ai", "text": "An answer."},
                {"role": "user", "text": "A second question?"},
                {"role": "ai", "text": "A second answer."},
            ],
            ai_settings=ai_settings,
            permitted_s3_keys=permitted_file_keys,
        )
        redbox_state = mock_run.call_args.args[0]  # pulls out the args that redbox.run was called with

        assert (
            redbox_state.request == expected_request
        ), f"Expected {expected_request}. Received: {redbox_state.request}"


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

    def _convert_input(self, prompt):
        if isinstance(prompt, dict):
            prompt = prompt["request"].question
        return super()._convert_input(prompt)

    async def astream_events(self, *_args, **_kwargs):
        for response in self.responses:
            yield response


@pytest.fixture()
def mocked_connect(uploaded_file: File) -> Connect:
    responses = [
        {
            "event": "on_chat_model_stream",
            "tags": [FINAL_RESPONSE_TAG],
            "data": {"chunk": Token(content="Good afternoon, ")},
        },
        {"event": "on_chat_model_stream", "tags": [FINAL_RESPONSE_TAG], "data": {"chunk": Token(content="Mr. Amor.")}},
        {"event": "on_chain_end", "tags": [ROUTE_NAME_TAG], "data": {"output": {"route_name": "gratitude"}}},
        {
            "event": "on_retriever_end",
            "tags": [SOURCE_DOCUMENTS_TAG],
            "data": {
                "output": [
                    Document(
                        metadata={"uri": uploaded_file.unique_name},
                        page_content="Good afternoon Mr Amor",
                    )
                ]
            },
        },
        {
            "event": "on_retriever_end",
            "tags": [SOURCE_DOCUMENTS_TAG],
            "data": {
                "output": [
                    Document(
                        metadata={"uri": uploaded_file.unique_name},
                        page_content="Good afternoon Mr Amor",
                    ),
                    Document(
                        metadata={"uri": uploaded_file.unique_name, "page_number": [34, 35]},
                        page_content="Good afternoon Mr Amor",
                    ),
                ]
            },
        },
        {
            "event": "on_custom_event",
            "name": "on_metadata_generation",
            "data": RequestMetadata(
                llm_calls=[LLMCallMetadata(llm_model_name="gpt-4o", input_tokens=123, output_tokens=1000)],
                selected_files_total_tokens=1000,
                number_of_selected_files=1,
            ),
        },
        {
            "event": "on_custom_event",
            "name": "activity",
            "data": RedboxActivityEvent(
                message="fish and chips",
            ),
        },
    ]

    return CannedGraphLLM(responses=responses)


@pytest.fixture()
def mocked_connect_with_naughty_citation(uploaded_file: File) -> CannedGraphLLM:
    responses = [
        {
            "event": "on_chat_model_stream",
            "tags": [FINAL_RESPONSE_TAG],
            "data": {"chunk": Token(content="Good afternoon, Mr. Amor.")},
        },
        {"event": "on_chain_end", "tags": [ROUTE_NAME_TAG], "data": {"output": {"route_name": "gratitude"}}},
        {
            "event": "on_retriever_end",
            "tags": [SOURCE_DOCUMENTS_TAG],
            "data": {
                "output": [
                    Document(
                        metadata={"uri": uploaded_file.unique_name},
                        page_content="Good afternoon Mr Amor",
                    ),
                    Document(
                        metadata={"uri": uploaded_file.unique_name},
                        page_content="I shouldn't send a \x00",
                    ),
                ]
            },
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
            "tags": [FINAL_RESPONSE_TAG],
            "data": {"chunk": Token(content="Good afternoon, ")},
        },
        {
            "event": "on_chat_model_stream",
            "tags": [FINAL_RESPONSE_TAG],
            "data": {"chunk": Token(content=error_messages.CORE_ERROR_MESSAGE)},
        },
    ]

    return CannedGraphLLM(responses=responses)


@pytest.fixture()
def mocked_connect_with_rate_limited_error() -> CannedGraphLLM:
    responses = [
        {
            "event": "on_chat_model_stream",
            "tags": [FINAL_RESPONSE_TAG],
            "data": {"chunk": Token(content="Good afternoon, ")},
        },
        {
            "event": "on_chat_model_stream",
            "tags": [FINAL_RESPONSE_TAG],
            "data": {"chunk": Token(content=error_messages.RATE_LIMITED)},
        },
    ]

    return CannedGraphLLM(responses=responses)


@pytest.fixture()
def mocked_connect_with_explicit_no_document_selected_error() -> CannedGraphLLM:
    responses = [
        {
            "event": "on_chat_model_stream",
            "tags": [FINAL_RESPONSE_TAG],
            "data": {"chunk": Token(content=error_messages.SELECT_DOCUMENT)},
        },
    ]

    return CannedGraphLLM(responses=responses)


@pytest.fixture()
def mocked_connect_agentic_search(uploaded_file: File) -> Connect:
    responses = [
        {
            "event": "on_custom_event",
            "name": "response_tokens",
            "data": "Good afternoon, ",
        },
        {
            "event": "on_custom_event",
            "name": "response_tokens",
            "data": "Mr. Amor.",
        },
        {"event": "on_chain_end", "tags": [ROUTE_NAME_TAG], "data": {"output": {"route_name": "search/agentic"}}},
        {
            "event": "on_custom_event",
            "name": "on_source_report",
            "data": [
                Document(metadata={"uri": uploaded_file.unique_name}, page_content="Good afternoon Mr Amor"),
                Document(metadata={"uri": uploaded_file.unique_name}, page_content="Good afternoon Mr Amor"),
                Document(
                    metadata={"uri": uploaded_file.unique_name, "page_number": [34, 35]},
                    page_content="Good afternoon Mr Amor",
                ),
            ],
        },
        {
            "event": "on_custom_event",
            "name": "on_metadata_generation",
            "data": RequestMetadata(
                llm_calls=[LLMCallMetadata(llm_model_name="gpt-4o", input_tokens=123, output_tokens=1000)],
                selected_files_total_tokens=1000,
                number_of_selected_files=1,
            ),
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
                "data": [{"s3_key": f.unique_name, "page_content": "a secret forth answer"} for f in several_files[2:]],
            }
        ),
        json.dumps({"resource_type": "end"}),
    ]
    return mocked_connect


@database_sync_to_async
def refresh_from_db(obj: Model) -> None:
    obj.refresh_from_db()
