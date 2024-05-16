import logging
import uuid
from http import HTTPStatus

import pytest
from botocore.exceptions import ClientError
from django.conf import settings
from django.test import Client
from redbox_app.redbox_core.models import (
    ChatHistory,
    ChatMessage,
    ChatRoleEnum,
    File,
    ProcessingStatusEnum,
    User,
)
from requests_mock import Mocker
from yarl import URL

from django_app.redbox_app.redbox_core.auth_views import get_or_create_user

logger = logging.getLogger(__name__)


@pytest.mark.django_db
def test_declaration_view_get(peter_rabbit, client):
    client.force_login(peter_rabbit)
    response = client.get("/")
    assert response.status_code == 200, response.status_code


def count_s3_objects(s3_client) -> int:
    paginator = s3_client.get_paginator("list_objects")
    return sum(len(result.get("Contents", [])) for result in paginator.paginate(Bucket=settings.BUCKET_NAME) if result)


def file_exists(s3_client, file_name) -> bool:
    """
    if the file key exists return True otherwise False
    """
    try:
        s3_client.get_object(Bucket=settings.BUCKET_NAME, Key=file_name.replace(" ", "_"))
        return True
    except ClientError as client_error:
        if client_error.response["Error"]["Code"] == "NoSuchKey":
            return False
        raise client_error


@pytest.mark.django_db
def test_upload_view(alice, client, file_pdf_path, s3_client, requests_mock):
    """
    Given that the object store does not have a file with our test file in it
    When we POST our test file to /upload/
    We Expect to see this file in the object store
    """
    file_name = file_pdf_path.split("/")[-1]

    # we begin by removing any file in minio that has this key
    s3_client.delete_object(Bucket=settings.BUCKET_NAME, Key=file_name.replace(" ", "_"))

    assert not file_exists(s3_client, file_name)

    client.force_login(alice)

    # we mock the response from the core-api
    mocked_response = {
        "key": file_name,
        "bucket": settings.BUCKET_NAME,
        "uuid": str(uuid.uuid4()),
    }
    requests_mock.post(
        f"http://{settings.CORE_API_HOST}:{settings.CORE_API_PORT}/file",
        status_code=201,
        json=mocked_response,
    )

    with open(file_pdf_path, "rb") as f:
        response = client.post("/upload/", {"uploadDoc": f})

        assert file_exists(s3_client, file_name)
        assert response.status_code == 302
        assert response.url == "/documents/"


@pytest.mark.django_db
def test_document_upload_status(client, alice, file_pdf_path, s3_client, requests_mock):
    file_name = file_pdf_path.split("/")[-1]

    # we begin by removing any file in minio that has this key
    s3_client.delete_object(Bucket=settings.BUCKET_NAME, Key=file_name.replace(" ", "_"))

    assert not file_exists(s3_client, file_name)
    client.force_login(alice)
    previous_count = count_s3_objects(s3_client)

    mocked_response = {
        "key": file_name,
        "bucket": settings.BUCKET_NAME,
        "uuid": str(uuid.uuid4()),
    }
    requests_mock.post(
        f"http://{settings.CORE_API_HOST}:{settings.CORE_API_PORT}/file",
        status_code=201,
        json=mocked_response,
    )

    with open(file_pdf_path, "rb") as f:
        response = client.post("/upload/", {"uploadDoc": f})

        assert response.status_code == 302
        assert response.url == "/documents/"
        assert count_s3_objects(s3_client) == previous_count + 1
        uploaded_file = File.objects.filter(user=alice).order_by("-created_at")[0]
        assert uploaded_file.processing_status == ProcessingStatusEnum.uploaded


@pytest.mark.django_db
def test_upload_view_duplicate_files(alice, bob, client, file_pdf_path, s3_client, requests_mock):
    # we mock the response from the core-api
    mocked_response = {
        "key": "file_key",
        "bucket": settings.BUCKET_NAME,
        "uuid": str(uuid.uuid4()),
    }
    requests_mock.post(
        f"http://{settings.CORE_API_HOST}:{settings.CORE_API_PORT}/file",
        status_code=201,
        json=mocked_response,
    )

    previous_count = count_s3_objects(s3_client)
    client.force_login(alice)

    with open(file_pdf_path, "rb") as f:
        client.post("/upload/", {"uploadDoc": f})
        response = client.post("/upload/", {"uploadDoc": f})

        assert response.status_code == 302
        assert response.url == "/documents/"

        assert count_s3_objects(s3_client) == previous_count + 2

        client.force_login(bob)
        response = client.post("/upload/", {"uploadDoc": f})

        assert response.status_code == 302
        assert response.url == "/documents/"

        assert count_s3_objects(s3_client) == previous_count + 3

        assert (
            File.objects.order_by("-created_at")[0].unique_name != File.objects.order_by("-created_at")[1].unique_name
        )


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
def test_upload_view_no_file(alice, client):
    client.force_login(alice)

    response = client.post("/upload/")

    assert response.status_code == 200
    assert "No document selected" in str(response.content)


@pytest.mark.django_db
def test_post_message_to_new_session(alice: User, client: Client, requests_mock: Mocker):
    # Given
    client.force_login(alice)
    rag_url = f"http://{settings.CORE_API_HOST}:{settings.CORE_API_PORT}/chat/rag"
    requests_mock.register_uri(
        "POST",
        rag_url,
        json={"output_text": "Good afternoon, Mr. Amor.", "source_documents": []},
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
    rag_url = f"http://{settings.CORE_API_HOST}:{settings.CORE_API_PORT}/chat/rag"
    requests_mock.register_uri(
        "POST",
        rag_url,
        json={"output_text": "Good afternoon, Mr. Amor.", "source_documents": []},
    )

    # When
    response = client.post("/post-message/", {"message": "Are you there?", "session-id": session_id})

    # Then
    assert response.status_code == HTTPStatus.FOUND
    assert URL(response.url).parts[-2] == str(session_id)
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
def test_get_user_existing(alice):
    assert get_or_create_user(alice.email) == alice


@pytest.mark.parametrize("email, admitted", [("alice@cabinetoffice.gov.uk", True), ("alice@hmrc.gov.uk", False)])
@pytest.mark.django_db
def test_get_user_new_cabinet_office(email, admitted):
    # user doesnt exist initially
    assert not User.objects.filter(email=email).exists()

    get_or_create_user(email)

    # only cabinet-office users are accepted
    assert User.objects.filter(email=email).exists() == admitted
