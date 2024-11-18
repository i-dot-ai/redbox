import logging
from http import HTTPStatus

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
