import logging
from http import HTTPStatus

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

User = get_user_model()

logger = logging.getLogger(__name__)


@pytest.mark.django_db()
def test_sign_in_view_redirect_to_sign_in(alice: User, client: Client):
    # Given a user that does exist in the db Alice

    # When
    url = reverse("log-in")
    response = client.post(url, data={"email": alice.email})

    # Then
    assert response.status_code == HTTPStatus.FOUND
    assert response.url == "/accounts/oidc/gds/login/"
