import logging
import uuid
from http import HTTPStatus
from pathlib import Path

import pytest
from botocore.exceptions import ClientError
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from redbox_app.redbox_core.models import File

User = get_user_model()

logger = logging.getLogger(__name__)


@pytest.mark.django_db()
def test_upload_view(alice, client, file_pdf_path: Path, s3_client):
    """
    Given that the object store does not have a file with our test file in it
    When we POST our test file to /upload/
    We Expect to see this file in the object store
    """
    file_name = f"{alice.email}/{file_pdf_path.name}"

    # we begin by removing any file in minio that has this key
    s3_client.delete_object(Bucket=settings.BUCKET_NAME, Key=file_name.replace(" ", "_"))

    assert not file_exists(s3_client, file_name)

    client.force_login(alice)

    with file_pdf_path.open("rb") as f:
        response = client.post("/upload/", {"uploadDocs": f})

        assert file_exists(s3_client, file_name)
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == "/documents/"


@pytest.mark.django_db()
def test_document_upload_status(client, alice, file_pdf_path: Path, s3_client):
    file_name = f"{alice}/{file_pdf_path.name}"

    # we begin by removing any file in minio that has this key
    s3_client.delete_object(Bucket=settings.BUCKET_NAME, Key=file_name.replace(" ", "_"))

    assert not file_exists(s3_client, file_name)
    client.force_login(alice)
    previous_count = count_s3_objects(s3_client)

    with file_pdf_path.open("rb") as f:
        response = client.post("/upload/", {"uploadDocs": f})

        assert response.status_code == HTTPStatus.FOUND
        assert response.url == "/documents/"
        assert count_s3_objects(s3_client) == previous_count + 1
        uploaded_file = File.objects.filter(user=alice).order_by("-created_at")[0]
        assert uploaded_file.status == File.Status.processing


@pytest.mark.django_db()
def test_upload_view_duplicate_files(alice, bob, client, file_pdf_path: Path, s3_client):
    # delete all alice's files
    for key in s3_client.list_objects(Bucket=settings.BUCKET_NAME, Prefix=alice.email).get("Contents", []):
        s3_client.delete_object(Bucket=settings.BUCKET_NAME, Key=key["Key"])

    # delete all bob's files
    for key in s3_client.list_objects(Bucket=settings.BUCKET_NAME, Prefix=bob.email).get("Contents", []):
        s3_client.delete_object(Bucket=settings.BUCKET_NAME, Key=key["Key"])

    previous_count = count_s3_objects(s3_client)

    def upload_file():
        with file_pdf_path.open("rb") as f:
            client.post("/upload/", {"uploadDocs": f})
            response = client.post("/upload/", {"uploadDocs": f})

            assert response.status_code == HTTPStatus.FOUND
            assert response.url == "/documents/"

            return File.objects.order_by("-created_at")[0]

    client.force_login(alice)
    alices_file = upload_file()

    assert count_s3_objects(s3_client) == previous_count + 1  # new file added
    assert alices_file.unique_name.startswith(alice.email)

    client.force_login(bob)
    bobs_file = upload_file()

    assert count_s3_objects(s3_client) == previous_count + 2  # new file added
    assert bobs_file.unique_name.startswith(bob.email)

    bobs_new_file = upload_file()

    assert count_s3_objects(s3_client) == previous_count + 2  # no change, duplicate file
    assert bobs_new_file.unique_name == bobs_file.unique_name


@pytest.mark.django_db()
def test_upload_view_bad_data(alice, client, file_py_path: Path, s3_client):
    previous_count = count_s3_objects(s3_client)
    client.force_login(alice)

    with file_py_path.open("rb") as f:
        response = client.post("/upload/", {"uploadDocs": f})

        assert response.status_code == HTTPStatus.OK
        assert "File type .py not supported" in str(response.content)
        assert count_s3_objects(s3_client) == previous_count


@pytest.mark.django_db()
def test_upload_view_no_file(alice, client):
    client.force_login(alice)

    response = client.post("/upload/")

    assert response.status_code == HTTPStatus.OK
    assert "No document selected" in str(response.content)


@pytest.mark.django_db()
def test_remove_doc_view(client: Client, alice: User, file_pdf_path: Path, s3_client: Client):
    file_name = f"{alice.email}/{file_pdf_path.name}"

    client.force_login(alice)
    # we begin by removing any file in minio that has this key
    s3_client.delete_object(Bucket=settings.BUCKET_NAME, Key=file_name.replace(" ", "_"))

    previous_count = count_s3_objects(s3_client)

    with file_pdf_path.open("rb") as f:
        # create file before testing deletion
        client.post("/upload/", {"uploadDocs": f})
        assert file_exists(s3_client, file_name)
        assert count_s3_objects(s3_client) == previous_count + 1

        new_file = File.objects.filter(user=alice).order_by("-created_at")[0]

        client.post(f"/remove-doc/{new_file.id}", {"doc_id": new_file.id})
        assert not file_exists(s3_client, file_name)
        assert count_s3_objects(s3_client) == previous_count
        assert File.objects.get(id=new_file.id).status == File.Status.deleted


@pytest.mark.django_db()
def test_remove_nonexistent_doc(alice: User, client: Client):
    # Given
    client.force_login(alice)
    nonexistent_uuid = uuid.uuid4()

    # When
    url = reverse("remove-doc", kwargs={"doc_id": nonexistent_uuid})
    response = client.get(url)

    # Then
    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.django_db()
def test_file_status_api_view_nonexistent_file(alice: User, client: Client):
    # Given
    client.force_login(alice)
    nonexistent_uuid = uuid.uuid4()

    # When
    response = client.get("/file-status/", {"id": nonexistent_uuid})

    # Then
    assert response.status_code == HTTPStatus.NOT_FOUND


def count_s3_objects(s3_client) -> int:
    paginator = s3_client.get_paginator("list_objects")
    return sum(len(result.get("Contents", [])) for result in paginator.paginate(Bucket=settings.BUCKET_NAME) if result)


def file_exists(s3_client, file_name) -> bool:
    """
    if the file key exists return True otherwise False
    """
    try:
        s3_client.get_object(Bucket=settings.BUCKET_NAME, Key=file_name.replace(" ", "_"))
    except ClientError as client_error:
        if client_error.response["Error"]["Code"] == "NoSuchKey":
            return False
        raise
    else:
        return True
