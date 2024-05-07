import json
import logging

import pytest
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.conf import settings
from django.test import Client
from redbox_app.redbox_core.consumers import ChatConsumer
from redbox_app.redbox_core.models import User
from requests_mock import Mocker

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


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

    await communicator.send_to(text_data=json.dumps({"message": "Are you there?"}))
    response = await communicator.receive_from()
    logger.debug(f"{response=}")

    # Then
    assert response == "Good afternoon, Mr. Amor."
    # Close
    await communicator.disconnect()


@database_sync_to_async
def create_user(email, client: Client):
    user = User.objects.create_user(email, password="")
    client.force_login(user)
    return user
