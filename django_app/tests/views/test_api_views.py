import logging
from http import HTTPStatus
from uuid import UUID

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

User = get_user_model()

logger = logging.getLogger(__name__)


@pytest.mark.django_db()
def test_api_view(user_with_chats_with_messages_over_time: User, client: Client):
    # Given
    client.force_login(user_with_chats_with_messages_over_time)

    # When
    url = reverse("user-view")
    response = client.get(url)

    # Then
    assert response.status_code == HTTPStatus.OK
    assert response.json()["email"] == user_with_chats_with_messages_over_time.email


@pytest.mark.django_db()
def test_api_view_fail(client: Client):
    # Given that the user is not logged in

    # When
    url = reverse("user-view")
    response = client.get(url)

    # Then
    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response.json() == {"detail": "Authentication credentials were not provided."}


@pytest.mark.django_db()
def test_file_upload(alice: User, original_file, chat, client: Client):
    # Given that alice is logged in
    client.force_login(alice)

    url = reverse("file-upload")
    response = client.post(url, {"file": original_file, "chat_id": chat.id})
    assert response.status_code == 200
    assert UUID(response.json()["file_id"])


@pytest.mark.django_db()
def test_file_upload_no_chat(alice: User, original_file, client: Client):
    # Given that alice is logged in
    client.force_login(alice)

    url = reverse("file-upload")
    response = client.post(url, {"file": original_file})
    assert response.status_code == 400
    assert response.json()["chat_id"] == ["This field is required."]


@pytest.mark.django_db()
def test_file_upload_invalid_file(chat, client: Client):
    # Given that alice is logged in
    client.force_login(chat.user)

    url = reverse("file-upload")
    response = client.post(url, {"file": 123, "chat_id": chat.id})
    assert response.status_code == 400
    assert response.json()["file"] == ["The submitted data was not a file. Check the encoding type on the form."]


@pytest.mark.django_db()
def test_file_upload_not_logged_in(original_file, chat, client: Client):
    # Given that alice is not logged in

    url = reverse("file-upload")
    response = client.post(url, {"file": original_file, "chat": chat.id})
    assert response.status_code == 403
    assert response.json()["detail"] == "Authentication credentials were not provided."
