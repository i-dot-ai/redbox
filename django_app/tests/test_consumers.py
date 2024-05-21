import json
import logging
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from redbox_app.redbox_core.consumers import ChatConsumer
from redbox_app.redbox_core.models import ChatHistory, ChatMessage, ChatRoleEnum, File, User
from websockets import WebSocketClientProtocol
from websockets.legacy.client import Connect

logger = logging.getLogger(__name__)


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_chat_consumer_with_new_session(client: Client):
    # Given
    carlos = await create_user("carlos@example.com", client)
    files: list[File] = await create_files(carlos)
    mocked_connect: Connect = create_mocked_connect([file.core_file_uuid for file in files])

    # When
    with patch("redbox_app.redbox_core.consumers.connect", new=mocked_connect):
        communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), "/ws/chat/")
        communicator.scope["user"] = carlos
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
        assert response4["type"] == "source"
        assert response4["data"]["original_file_name"] == "original_file_0.txt"
        assert response5["type"] == "source"
        assert response5["data"]["original_file_name"] == "original_file_1.txt"
        # Close
        await communicator.disconnect()

    assert await get_chat_message_text(carlos, ChatRoleEnum.user) == "Hello Hal."
    assert await get_chat_message_text(carlos, ChatRoleEnum.ai) == "Good afternoon, Mr. Amor."


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_chat_consumer_with_existing_session(client: Client):
    # Given
    carol = await create_user("carol@example.com", client)
    files: list[File] = await create_files(carol)
    mocked_connect: Connect = create_mocked_connect([file.core_file_uuid for file in files])
    session = await create_chat_history(carol)

    # When
    with patch("redbox_app.redbox_core.consumers.connect", new=mocked_connect):
        communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), "/ws/chat/")
        communicator.scope["user"] = carol
        connected, subprotocol = await communicator.connect()
        assert connected

        await communicator.send_json_to({"message": "Hello Hal.", "sessionId": str(session.id)})
        response1 = await communicator.receive_json_from(timeout=5)
        response2 = await communicator.receive_json_from(timeout=5)
        response3 = await communicator.receive_json_from(timeout=5)
        response4 = await communicator.receive_json_from(timeout=5)
        response5 = await communicator.receive_json_from(timeout=5)

        # Then
        assert response1["type"] == "session-id"
        assert response1["data"] == str(session.id)
        assert response2["type"] == "text"
        assert response2["data"] == "Good afternoon, "
        assert response3["type"] == "text"
        assert response3["data"] == "Mr. Amor."
        assert response4["type"] == "source"
        assert response4["data"]["original_file_name"] == "original_file_0.txt"
        assert response5["type"] == "source"
        assert response5["data"]["original_file_name"] == "original_file_1.txt"
        # Close
        await communicator.disconnect()

    assert await get_chat_message_text(carol, ChatRoleEnum.user) == "Hello Hal."
    assert await get_chat_message_text(carol, ChatRoleEnum.ai) == "Good afternoon, Mr. Amor."


@database_sync_to_async
def get_chat_message_text(user: User, role: ChatRoleEnum) -> str:
    return ChatMessage.objects.get(chat_history__users=user, role=role).text


@database_sync_to_async
def create_user(email: str, client: Client) -> User:
    user = User.objects.create_user(email, password="")
    client.force_login(user)
    return user


@database_sync_to_async
def create_chat_history(user: User) -> ChatHistory:
    session_id = uuid.uuid4()
    chat_history = ChatHistory.objects.create(id=session_id, users=user)
    return chat_history


@database_sync_to_async
def create_files(user: User):
    return [
        File.objects.create(
            user=user,
            core_file_uuid=uuid.uuid4(),
            original_file_name=f"original_file_{i}.txt",
            original_file=SimpleUploadedFile(f"original_file_{i}.txt", b"Lorem Ipsum."),
        )
        for i in range(2)
    ]


def create_mocked_connect(file_uuids: list[uuid.UUID]) -> Connect:
    mocked_websocket = AsyncMock(spec=WebSocketClientProtocol, name="mocked_websocket")
    mocked_connect = MagicMock(spec=Connect, name="mocked_connect")
    mocked_connect.return_value.__aenter__.return_value = mocked_websocket
    mocked_websocket.__aiter__.return_value = [
        json.dumps({"resource_type": "text", "data": "Good afternoon, "}),
        json.dumps({"resource_type": "text", "data": "Mr. Amor."}),
        json.dumps({"resource_type": "documents", "data": [{"file_uuid": str(u)} for u in file_uuids]}),
        json.dumps({"resource_type": "end"}),
    ]
    return mocked_connect
