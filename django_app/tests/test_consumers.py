import json
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from redbox_app.redbox_core.consumers import ChatConsumer
from redbox_app.redbox_core.models import ChatHistory, ChatMessage, ChatRoleEnum, File, User
from websockets import WebSocketClientProtocol
from websockets.legacy.client import Connect

logger = logging.getLogger(__name__)


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_chat_consumer_with_new_session(alice: User, uploaded_file: File):
    # Given
    mocked_connect: Connect = create_mocked_connect(uploaded_file)

    # When
    with patch("redbox_app.redbox_core.consumers.connect", new=mocked_connect):
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
        assert response2["data"] == "Good afternoon, "
        assert response3["type"] == "text"
        assert response3["data"] == "Mr. Amor."
        assert response4["type"] == "source"
        assert response4["data"]["original_file_name"] == uploaded_file.original_file_name
        # Close
        await communicator.disconnect()

    assert await get_chat_message_text(alice, ChatRoleEnum.user) == "Hello Hal."
    assert await get_chat_message_text(alice, ChatRoleEnum.ai) == "Good afternoon, Mr. Amor."


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_chat_consumer_with_existing_session(alice: User, uploaded_file: File, chat_history: ChatHistory):
    # Given
    mocked_connect: Connect = create_mocked_connect(uploaded_file)

    # When
    with patch("redbox_app.redbox_core.consumers.connect", new=mocked_connect):
        communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), "/ws/chat/")
        communicator.scope["user"] = alice
        connected, _ = await communicator.connect()
        assert connected

        await communicator.send_json_to({"message": "Hello Hal.", "sessionId": str(chat_history.id)})
        response1 = await communicator.receive_json_from(timeout=5)

        # Then
        assert response1["type"] == "session-id"
        assert response1["data"] == str(chat_history.id)

        # Close
        await communicator.disconnect()

    assert await get_chat_message_text(alice, ChatRoleEnum.user) == "Hello Hal."
    assert await get_chat_message_text(alice, ChatRoleEnum.ai) == "Good afternoon, Mr. Amor."


@database_sync_to_async
def get_chat_message_text(user: User, role: ChatRoleEnum) -> str:
    return ChatMessage.objects.get(chat_history__users=user, role=role).text


def create_mocked_connect(file: File) -> Connect:
    mocked_websocket = AsyncMock(spec=WebSocketClientProtocol, name="mocked_websocket")
    mocked_connect = MagicMock(spec=Connect, name="mocked_connect")
    mocked_connect.return_value.__aenter__.return_value = mocked_websocket
    mocked_websocket.__aiter__.return_value = [
        json.dumps({"resource_type": "text", "data": "Good afternoon, "}),
        json.dumps({"resource_type": "text", "data": "Mr. Amor."}),
        json.dumps({"resource_type": "documents", "data": [{"file_uuid": str(file.core_file_uuid)}]}),
        json.dumps({"resource_type": "end"}),
    ]
    return mocked_connect
