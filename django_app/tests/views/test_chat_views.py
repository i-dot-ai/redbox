import json
import logging
import uuid
from http import HTTPStatus

import pytest
from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from redbox_app.redbox_core.models import (
    Chat,
    ChatMessage,
)

User = get_user_model()

logger = logging.getLogger(__name__)


@pytest.mark.django_db()
def test_user_can_see_their_own_chats(chat_with_messages_over_time: Chat, alice: User, client: Client):
    # Given
    client.force_login(alice)

    # When
    response = client.get(f"/chats/{chat_with_messages_over_time.id}/")

    # Then
    assert response.status_code == HTTPStatus.OK


@pytest.mark.django_db()
def test_user_cannot_see_other_users_chats(chat: Chat, bob: User, client: Client):
    # Given
    client.force_login(bob)

    # When
    response = client.get(f"/chats/{chat.id}/")

    # Then
    assert response.status_code == HTTPStatus.FOUND
    assert response.headers.get("Location") == "/chats/"


@pytest.mark.django_db()
def test_view_session_with_documents(chat_message: ChatMessage, client: Client):
    # Given
    client.force_login(chat_message.chat.user)
    chat_id = chat_message.chat.id

    # When
    response = client.get(f"/chats/{chat_id}/")

    # Then
    assert response.status_code == HTTPStatus.OK
    assert b"original_file.txt" in response.content


@pytest.mark.django_db()
def test_chat_grouped_by_age(user_with_chats_with_messages_over_time: User, client: Client):
    # Given
    client.force_login(user_with_chats_with_messages_over_time)

    # When
    response = client.get(reverse("chats"))

    # Then
    assert response.status_code == HTTPStatus.OK
    soup = BeautifulSoup(response.content)
    date_groups_all = soup.find_all("h3", {"class": "rb-chat-history__date_group"})

    # Filter out the date_group that is within a <template> tag (this is just for CSR)
    date_groups = [dg for dg in date_groups_all if not dg.find_parent("template")]

    assert len(date_groups) == 5
    for date_group, (header, chat_name) in zip(
        date_groups,
        [
            ("Today", "today"),
            ("Yesterday", "yesterday"),
            ("Previous 7 days", "5 days old"),
            ("Previous 30 days", "20 days old"),
            ("Older than 30 days", "40 days old"),
        ],
        strict=False,
    ):
        assert date_group.text == header
        assert date_group.find_next_sibling("ul").find("a").text == chat_name


@pytest.mark.django_db()
def test_nonexistent_chats(alice: User, client: Client):
    # Given
    client.force_login(alice)
    nonexistent_uuid = uuid.uuid4()

    # When
    url = reverse("chats", kwargs={"chat_id": nonexistent_uuid})
    response = client.get(url)

    # Then
    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.django_db()
def test_post_chat_title(alice: User, chat: Chat, client: Client):
    # Given
    client.force_login(alice)

    # When
    url = reverse("chat-titles", kwargs={"chat_id": chat.id})
    response = client.post(url, json.dumps({"name": "New chat name"}), content_type="application/json")

    # Then
    status = HTTPStatus(response.status_code)
    assert status.is_success
    chat.refresh_from_db()
    assert chat.name == "New chat name"


@pytest.mark.django_db()
def test_post_chat_title_with_naughty_string(alice: User, chat: Chat, client: Client):
    # Given
    client.force_login(alice)

    # When
    url = reverse("chat-titles", kwargs={"chat_id": chat.id})
    response = client.post(url, json.dumps({"name": "New chat name \x00"}), content_type="application/json")

    # Then
    status = HTTPStatus(response.status_code)
    assert status.is_success
    chat.refresh_from_db()
    assert chat.name == "New chat name \ufffd"


@pytest.mark.django_db()
def test_staff_user_can_see_route(chat_with_files: Chat, client: Client):
    # Given
    chat_with_files.user.is_staff = True
    chat_with_files.user.save()
    client.force_login(chat_with_files.user)

    # When
    response = client.get(f"/chats/{chat_with_files.id}/")

    # Then
    assert response.status_code == HTTPStatus.OK
    assert b"iai-chat-bubble__route" in response.content
    assert b"iai-chat-bubble__route govuk-!-display-none" not in response.content
