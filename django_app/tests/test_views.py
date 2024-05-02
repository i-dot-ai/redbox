import logging

import pytest
import uuid
from django.conf import settings
from django.test import Client
from redbox_app.redbox_core.models import User, ChatHistory, ChatMessage, ChatRoleEnum
from http import HTTPStatus
from yarl import URL
from redbox_app.redbox_core.utils import build_rag_url
from requests_mock import Mocker

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


@pytest.mark.django_db
def test_declaration_view_get(peter_rabbit, client):
    client.force_login(peter_rabbit)
    response = client.get("/")
    assert response.status_code == 200, response.status_code


def count_s3_objects(s3_client) -> int:
    paginator = s3_client.get_paginator("list_objects")
    return sum(len(result.get("Contents", [])) for result in paginator.paginate(Bucket=settings.BUCKET_NAME) if result)


@pytest.mark.django_db
def test_upload_view(alice, client, file_pdf_path, s3_client):
    previous_count = count_s3_objects(s3_client)
    client.force_login(alice)

    with open(file_pdf_path, "rb") as f:
        response = client.post("/upload/", {"uploadDoc": f})

        assert response.status_code == 200
        assert "Your file has been uploaded" in str(response.content)

        assert count_s3_objects(s3_client) == previous_count + 1


@pytest.mark.django_db
def test_upload_view_bad_data(alice, client, file_py_path, s3_client):
    previous_count = count_s3_objects(s3_client)
    client.force_login(alice)

    with open(file_py_path, "rb") as f:
        response = client.post("/upload/", {"uploadDoc": f})

        assert response.status_code == 200
        assert "File type .py not supported" in str(response.content)
        assert count_s3_objects(s3_client) == previous_count


@pytest.mark.django_db
def test_post_message_to_new_session(alice: User, client: Client, requests_mock: Mocker):
    # Given
    client.force_login(alice)
    requests_mock.register_uri(
        "POST", str(build_rag_url()), json={"response_message": {"text": "Good afternoon, Mr. Amor."}}
    )

    # When
    response = client.post("/post-message/", {"message": "Are you there?"})

    # Then
    assert response.status_code == HTTPStatus.FOUND
    assert "Location" in response.headers
    session_id = URL(response.url).parts[-2]
    assert (
        ChatMessage.objects.filter(chat_history__id=session_id, role=ChatRoleEnum.user).first().text == "Are you there?"
    )
    assert (
        ChatMessage.objects.filter(chat_history__id=session_id, role=ChatRoleEnum.ai).first().text
        == "Good afternoon, Mr. Amor."
    )


@pytest.mark.django_db
def test_post_message_to_existing_session(alice: User, client: Client, requests_mock: Mocker):
    # Given
    client.force_login(alice)
    session_id = uuid.uuid4()
    logger.debug(f"{session_id=}")
    ChatHistory.objects.create(id=session_id, users=alice)
    requests_mock.register_uri(
        "POST", str(build_rag_url()), json={"response_message": {"text": "Good afternoon, Mr. Amor."}}
    )

    # When
    response = client.post("/post-message/", {"message": "Are you there?", "session-id": session_id})

    # Then
    assert response.status_code == HTTPStatus.FOUND
    assert response.headers.get("Location").endswith(f"{session_id}/")
    assert (
        ChatMessage.objects.filter(chat_history__id=session_id, role=ChatRoleEnum.user).first().text == "Are you there?"
    )
    assert (
        ChatMessage.objects.filter(chat_history__id=session_id, role=ChatRoleEnum.ai).first().text
        == "Good afternoon, Mr. Amor."
    )
