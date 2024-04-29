import os
import re
import time

import pytest
import requests

# TODO: add e2e tests involving the Django app, checking S3 upload


def test_upload_to_search(file_path, s3_client):
    """
    When I POST file data to core-api/file
    I Expect:
        the file to be chunked
        embeddings to be produced for all chunks
    And,
    When I ask a question relevant to my file
    I expect the file to be cited in the response
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
        )
        assert response.status_code == 200
        file_uuid = response.json()["uuid"]

        timeout = 120
        start_time = time.time()
        error = None
        embedding_complete = False

        while time.time() - start_time < timeout:
            time.sleep(5)
            chunk_response = requests.get(f"http://localhost:5002/file/{file_uuid}/status")
            if chunk_response.status_code == 200 and chunk_response.json()["processing_status"] == "complete":
                embedding_complete = True
                break  # test passed
            else:
                error = chunk_response.text

        if not embedding_complete:
            pytest.fail(reason=f"failed to get embedded chunks within {timeout} seconds, potential error: {error}")

        rag_response = requests.post(
            "http://localhost:5002/chat/rag",
            json={
                "message_history": [
                    {"role": "system", "text": "You are a helpful AI Assistant"},
                    {"role": "user", "text": "Who is the prime minister"},
                ]
            },
        )
        assert rag_response.status_code == 200
        response_message_text = rag_response.json()["response_message"]["text"]
        assert "Rishi Sunak" in response_message_text
        assert re.findall(r"<Doc\w{8}-\w{4}-\w{4}-\w{4}-\w{12}>", response_message_text)
