import os
import re
import time
from uuid import UUID, uuid4

import pytest
import requests
from jose import jwt
from playwright.sync_api import Page, expect

# TODO: add e2e tests involving the Django app, checking S3 upload

USER_UUIDS: list[UUID] = [uuid4(), uuid4()]


def make_headers(user_uuid: UUID):
    token = jwt.encode({"user_uuid": str(user_uuid)}, key="super-secure-private-key")
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.incremental
class TestEndToEnd:
    file_uuids: dict[UUID, str] = {}
    source_document_file_uuids: dict[UUID, set[str]] = {}

    @pytest.mark.parametrize("user_uuid", USER_UUIDS)
    def test_upload_to_search(self, file_path, s3_client, user_uuid):
        """
        Given that I have uploaded a file to s3
        When I POST the file key to core-api/file
        I Expect a file uuid to be returned
        """
        with open(file_path, "rb") as f:
            file_key = os.path.basename(file_path)
            file_type = os.path.splitext(file_key)[-1]
            bucket_name = "redbox-storage-dev"
            s3_client.upload_fileobj(
                Bucket=bucket_name,
                Fileobj=f,
                Key=file_key,
                ExtraArgs={"Tagging": f"file_type={file_type}"},
            )

            response = requests.post(
                url="http://localhost:5002/file",
                json={
                    "key": file_key,
                    "bucket": bucket_name,
                },
                headers=make_headers(user_uuid),
                timeout=30,
            )
            TestEndToEnd.file_uuids[user_uuid] = response.json()["uuid"]
            assert response.status_code == 201

    @pytest.mark.parametrize("user_uuid", USER_UUIDS)
    def test_get_file_status(self, user_uuid):
        """
        Given that I have POSTed a file key to core-api/file
        When I GET the file status
        I Expect the file status to be "completed" within 120 seconds
        """
        timeout = 120
        start_time = time.time()
        error = None
        embedding_complete = False

        while time.time() - start_time < timeout:
            time.sleep(1)
            chunk_response = requests.get(
                f"http://localhost:5002/file/{TestEndToEnd.file_uuids[user_uuid]}/status",
                headers=make_headers(user_uuid),
                timeout=30,
            )
            if chunk_response.status_code == 200 and chunk_response.json()["processing_status"] == "complete":
                embedding_complete = True
                break  # test passed
            else:
                error = chunk_response.text

        if not embedding_complete:
            pytest.fail(reason=f"failed to get embedded chunks within {timeout} seconds, potential error: {error}")

    @pytest.mark.parametrize("user_uuid", USER_UUIDS)
    def test_get_file_chunks(self, user_uuid):
        """
        Given that I have POSTed a file key to core-api/file
        And the file status is complete
        When I GET the file chunks
        I Expect a 200 response code
        """
        chunks_response = requests.get(
            f"http://localhost:5002/file/{TestEndToEnd.file_uuids[user_uuid]}/chunks",
            headers=make_headers(user_uuid),
            timeout=30,
        )
        assert chunks_response.status_code == 200

    @pytest.mark.parametrize("user_uuid", USER_UUIDS)
    def test_post_rag(self, user_uuid):
        """
        Given that I have POSTed a file key to core-api/file
        And the file status is complete
        When I POST a question to the rag endpoint
        I Expect an answer and for the cited documents to be the one I uploaded
        """
        rag_response = requests.post(
            "http://localhost:5002/chat/rag",
            json={
                "message_history": [
                    {"role": "system", "text": "You are a helpful AI Assistant"},
                    {"role": "user", "text": "please summarise my document"},
                ]
            },
            headers=make_headers(user_uuid),
            timeout=30,
        )
        assert rag_response.status_code == 200
        source_document_file_uuids = {
            source_document["file_uuid"] for source_document in rag_response.json()["source_documents"]
        }

        assert TestEndToEnd.file_uuids[user_uuid] in source_document_file_uuids
        TestEndToEnd.source_document_file_uuids[user_uuid] = source_document_file_uuids

    @pytest.mark.parametrize("user_uuid", USER_UUIDS)
    def test_permissions(self, user_uuid):
        """
        Given that I have POSTed a file key to core-api/file
        And the file status is complete, And asked some RAG questions
        Even though the uploaded documents and RAG questions are identical
        I Expect that the sourced documents are only available to the user
        that uploaded them.
        """

        for other_user_uuid, source_document_file_uuids in TestEndToEnd.source_document_file_uuids.items():
            if other_user_uuid != user_uuid:
                assert TestEndToEnd.file_uuids[user_uuid] not in source_document_file_uuids


def test_landing_page(page: Page):
    page.goto("http://localhost:8090")

    # Expect a title "to contain" a substring.
    expect(page).to_have_title(re.compile("Redbox Copilot"))
