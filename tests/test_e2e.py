import os
import time

import pytest
import requests

# TODO: add e2e tests involving the Django app, checking S3 upload


@pytest.mark.incremental
class TestEndToEnd:
    """
    When I POST file data to core-api/file
    I Expect:
        the file to be chunked
        embeddings to be produced for all chunks
    And,
    When I ask a question relevant to my file
    I expect the file to be cited in the response
    """

    file_uuid: str = None

    def test_upload_to_search(self, file_path, s3_client):
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
            )
            TestEndToEnd.file_uuid = response.json()["uuid"]
            assert response.status_code == 200

    def test_get_file_status(self):
        timeout = 120
        start_time = time.time()
        error = None
        embedding_complete = False

        while time.time() - start_time < timeout:
            time.sleep(1)
            chunk_response = requests.get(f"http://localhost:5002/file/{TestEndToEnd.file_uuid}/status")
            if chunk_response.status_code == 200 and chunk_response.json()["processing_status"] == "complete":
                embedding_complete = True
                break  # test passed
            else:
                error = chunk_response.text

        if not embedding_complete:
            pytest.fail(reason=f"failed to get embedded chunks within {timeout} seconds, potential error: {error}")

    def test_get_file_chunks(self):
        chunks_response = requests.get(f"http://localhost:5002/file/{TestEndToEnd.file_uuid}/chunks")
        assert chunks_response.status_code == 200

    def test_post_rag(self):
        rag_response = requests.post(
            "http://localhost:5002/chat/rag",
            json={
                "message_history": [
                    {"role": "system", "text": "You are a helpful AI Assistant"},
                    {"role": "user", "text": "please summarise my document"},
                ]
            },
        )
        assert rag_response.status_code == 200
        source_document_file_uuids = {
            source_document["file_uuid"] for source_document in rag_response.json()["source_documents"]
        }
        assert TestEndToEnd.file_uuid in source_document_file_uuids
