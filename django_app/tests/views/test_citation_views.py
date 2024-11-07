import logging
import uuid
from collections.abc import Sequence
from http import HTTPStatus

import pytest
from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from redbox_app.redbox_core.models import (
    Chat,
    ChatMessage,
    Citation,
    File,
)

User = get_user_model()

logger = logging.getLogger(__name__)


@pytest.mark.django_db()
def test_citations_shown(client: Client, alice: User, chat: Chat, several_files: Sequence[File]):
    # Given
    client.force_login(alice)
    chat_message = ChatMessage.objects.create(chat=chat, text="Some answer.", role=ChatMessage.Role.ai)

    Citation.objects.create(file=several_files[0], chat_message=chat_message, text="Citation 1")
    Citation.objects.create(file=several_files[1], chat_message=chat_message, text="Citation 2")
    Citation.objects.create(
        source=Citation.Origin.WIKIPEDIA, url="https://wikipedia-test", chat_message=chat_message, text="Citation 3"
    )

    # When
    response = client.get(f"/citations/{chat_message.id}/")

    # Then
    assert response.status_code == HTTPStatus.OK
    soup = BeautifulSoup(response.content, features="html.parser")
    sources_panel = soup.select("ul.rb-citations__list")[0]
    files = sources_panel.find_all("h3")
    citation_items = sources_panel.find_all("markdown-converter")
    filenames = [h3.get_text().strip() for h3 in files]
    citations = [element.get_text().strip() for element in citation_items]

    assert filenames == ["original_file_0.txt", "original_file_1.txt", "https://wikipedia-test"]
    assert citations == ["Citation 1", "Citation 2", "Citation 3"]


@pytest.mark.django_db()
def test_user_can_see_their_own_citations(chat_message_with_citation: ChatMessage, alice: User, client: Client):
    # Given
    client.force_login(alice)

    # When
    response = client.get(f"/citations/{chat_message_with_citation.id}/")

    # Then
    assert response.status_code == HTTPStatus.OK


@pytest.mark.django_db()
def test_user_cannot_see_other_users_citations(chat_message_with_citation: Chat, bob: User, client: Client):
    # Given
    client.force_login(bob)

    # When
    response = client.get(f"/citations/{chat_message_with_citation.id}/")

    # Then
    assert response.status_code == HTTPStatus.FOUND
    assert response.headers.get("Location") == "/chats/"


@pytest.mark.django_db()
def test_nonexistent_citations(alice: User, client: Client):
    # Given
    client.force_login(alice)
    nonexistent_uuid = uuid.uuid4()

    # When
    url = reverse("citations", kwargs={"message_id": nonexistent_uuid})
    response = client.get(url)

    # Then
    assert response.status_code == HTTPStatus.NOT_FOUND
