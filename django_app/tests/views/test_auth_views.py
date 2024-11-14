import logging
from http import HTTPStatus

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

User = get_user_model()

logger = logging.getLogger(__name__)


@pytest.mark.django_db()
def test_sign_in_view_redirect_to_sign_in(alice: User, client: Client, mailoutbox):
    # Given a user that does exist in the db Alice

    # When
    url = reverse("sign-in")
    response = client.post(url, data={"email": alice.email})

    # Then
    assert response.status_code == HTTPStatus.FOUND
    assert response.url == "/sign-in-link-sent/"
    link = next(line for line in mailoutbox[-1].body.splitlines() if line.startswith("http"))
    signed_in_response = client.get(link)
    assert signed_in_response.status_code == HTTPStatus.OK


@pytest.mark.django_db()
def test_sign_in_view_redirect_sign_up(client: Client):
    # Given a user that does not exist in the database

    # When
    url = reverse("sign-in")
    response = client.post(url, data={"email": "not.a.real.user@gov.uk"})

    # Then
    assert response.status_code == HTTPStatus.FOUND
    assert response.url == "/sign-up-page-1"
