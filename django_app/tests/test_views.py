import logging
from http import HTTPStatus

import pytest
from django.conf import settings
from django.test import Client
from requests_mock import Mocker
from yarl import URL

from redbox_app.redbox_core.models import ChatHistory, ChatMessage, ChatRoleEnum, User

logger = logging.getLogger(__name__)


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

        assert response.status_code == 302
        assert response.url == "/documents/"
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
    rag_url = settings.CORE_API_HOST + ":" + settings.CORE_API_PORT + "/chat/rag"
    requests_mock.register_uri(
        "POST", rag_url, json={"output_text": "Good afternoon, Mr. Amor.", "source_documents": []}
    )

    # When
    response = client.post("/post-message/", {"message": "Are you there?"})

    # Then
    assert response.status_code == HTTPStatus.FOUND
    assert "Location" in response.headers
    session_id = URL(response.url).parts[-2]
    assert ChatMessage.objects.get(chat_history__id=session_id, role=ChatRoleEnum.user).text == "Are you there?"
    assert (
        ChatMessage.objects.get(chat_history__id=session_id, role=ChatRoleEnum.ai).text == "Good afternoon, Mr. Amor."
    )


@pytest.mark.django_db
def test_post_message_to_existing_session(chat_history: ChatHistory, client: Client, requests_mock: Mocker):
    # Given
    client.force_login(chat_history.users)
    session_id = chat_history.id
    rag_url = settings.CORE_API_HOST + ":" + settings.CORE_API_PORT + "/chat/rag"
    requests_mock.register_uri(
        "POST", rag_url, json={"output_text": "Good afternoon, Mr. Amor.", "source_documents": []}
    )

    # When
    response = client.post("/post-message/", {"message": "Are you there?", "session-id": session_id})

    # Then
    assert response.status_code == HTTPStatus.FOUND
    assert URL(response.url).parts[-2] == str(session_id)
    assert ChatMessage.objects.get(chat_history__id=session_id, role=ChatRoleEnum.user).text == "Are you there?"
    assert (
        ChatMessage.objects.get(chat_history__id=session_id, role=ChatRoleEnum.ai).text == "Good afternoon, Mr. Amor."
    )


@pytest.mark.django_db
def test_view_session_with_documents(chat_message: ChatMessage, client: Client):
    # Given
    client.force_login(chat_message.chat_history.users)
    session_id = chat_message.chat_history.id

    # When
    response = client.get(f"/sessions/{session_id}/")

    # Then
    assert response.status_code == HTTPStatus.OK
    assert b"uploaded_file.pdf" in response.content


@pytest.mark.django_db
def test_document_upload_status(client: Client, alice, file_pdf_path, s3_client):
    client.force_login(alice)
    previous_count = count_s3_objects(s3_client)

    with open(file_pdf_path, "rb") as f:
        response = client.post("/upload/", {"uploadDoc": f})

        assert response.status_code == 302
        assert response.url == "/documents/"
        assert count_s3_objects(s3_client) == previous_count + 1
        assert "Completed" in response.content
        assert "Unknown" not in response.content
