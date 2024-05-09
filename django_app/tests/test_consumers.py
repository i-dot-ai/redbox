import json
import logging
import uuid

import pytest
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.conf import settings
from django.test import Client
from redbox_app.redbox_core.consumers import ChatConsumer
from redbox_app.redbox_core.models import ChatMessage, ChatRoleEnum, User, ChatHistory
from requests_mock import Mocker

logger = logging.getLogger(__name__)


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_chat_consumer_with_new_session(client: Client, requests_mock: Mocker):
    # Given
    carlos = await create_user("carlos@example.com", client)

    rag_url = settings.CORE_API_HOST + ":" + settings.CORE_API_PORT + "/chat/rag"
    requests_mock.register_uri("POST", rag_url, json={"output_text": "Good afternoon, Mr. Amor."})

    # When
    communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), "/ws/chat/")
    communicator.scope["user"] = carlos
    connected, subprotocol = await communicator.connect()
    assert connected

    await communicator.send_to(text_data=json.dumps({"message": "Hello Hal."}))
    response = await communicator.receive_from(timeout=99)

    # Then
    assert response == "Good afternoon, Mr. Amor."
    # Close
    await communicator.disconnect()

    assert await get_chat_message_text(carlos, ChatRoleEnum.user) == "Hello Hal."
    assert await get_chat_message_text(carlos, ChatRoleEnum.ai) == "Good afternoon, Mr. Amor."


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_chat_consumer_with_existing_session(client: Client, requests_mock: Mocker):
    # Given
    carol = await create_user("carol@example.com", client)
    session = await create_chat_history(carol)

    rag_url = settings.CORE_API_HOST + ":" + settings.CORE_API_PORT + "/chat/rag"
    requests_mock.register_uri("POST", rag_url, json={"output_text": "Good afternoon, Mr. Amor."})

    # When
    communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), "/ws/chat/")
    communicator.scope["user"] = carol
    connected, subprotocol = await communicator.connect()
    assert connected

    await communicator.send_to(text_data=json.dumps({"message": "Hello Hal.", "sessionId": str(session.id)}))
    response = await communicator.receive_from(timeout=99)

    # Then
    assert response == "Good afternoon, Mr. Amor."
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
