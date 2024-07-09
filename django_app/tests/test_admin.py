import csv
import io
import logging
from http import HTTPStatus

import pytest
from django.test import Client
from django.urls import reverse

from redbox_app.redbox_core.models import ChatMessage, User

logger = logging.getLogger(__name__)


@pytest.mark.django_db()
def test_chat_history_export(superuser: User, chat_message_with_rating: ChatMessage, client: Client):
    # Given
    client.force_login(superuser)

    # When

    # See https://docs.djangoproject.com/en/dev/ref/contrib/admin/#reversing-admin-urls
    url = reverse("admin:redbox_core_chathistory_changelist")
    data = {"action": "export_as_csv", "_selected_action": [chat_message_with_rating.chat_history.pk]}
    response = client.post(url, data, follow=True)

    # Then
    assert response.status_code == HTTPStatus.OK
    rows = list(csv.DictReader(io.StringIO(response.content.decode("utf-8"))))
    assert len(rows) == 1
    row = rows[0]
    assert row["history_name"] == "A chat"
    assert row["history_users"] == "alice@cabinetoffice.gov.uk"
    assert row["message_text"] == "A question?"
    assert row["rating_rating"] == "3"
    assert row["rating_chips"] == "speed accuracy blasphemy"


@pytest.mark.django_db()
def test_chat_history_export_without_ratings(superuser: User, chat_message: ChatMessage, client: Client):
    # Given
    client.force_login(superuser)

    # When

    # See https://docs.djangoproject.com/en/dev/ref/contrib/admin/#reversing-admin-urls
    url = reverse("admin:redbox_core_chathistory_changelist")
    data = {"action": "export_as_csv", "_selected_action": [chat_message.chat_history.pk]}
    response = client.post(url, data, follow=True)

    # Then
    assert response.status_code == HTTPStatus.OK
    rows = list(csv.DictReader(io.StringIO(response.content.decode("utf-8"))))
    assert len(rows) == 1
    row = rows[0]
    assert row["history_name"] == "A chat"
    assert row["history_users"] == "alice@cabinetoffice.gov.uk"
    assert row["message_text"] == "A question?"
    assert row["rating_rating"] is None
    assert row["rating_chips"] is None
