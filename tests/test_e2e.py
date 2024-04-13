import os
import time

import pytest
import requests

# TODO: add e2e tests involving the Django app, checking S3 upload


def test_upload_to_elastic(file_pdf_path, s3_client):
    """
    When I POST file data to core-api/file
    I Expect a Chunk with a non-null embedding ... eventually
    """

    with open(file_pdf_path, "rb") as f:
        file_key = os.path.basename(file_pdf_path)
        bucket_name = "redbox-storage-dev"
        s3_client.upload_fileobj(
            Bucket=bucket_name,
            Fileobj=f,
            Key=file_key,
            ExtraArgs={"Tagging": "file_type=pdf"},
        )

        response = requests.post(
            url="http://localhost:5002/file",
            params={
                "name": file_key,
                "bucket": bucket_name,
            },
        )
        assert response.status_code == 200
        file_uuid = response.json()

        timeout = 120
        start_time = time.time()
        error = None

        while time.time() - start_time < timeout:
            time.sleep(1)
            chunk_response = requests.get(f"http://localhost:5002/file/{file_uuid}/status")
            if chunk_response.status_code == 200 and chunk_response.json()["processing_status"] == "complete":
                return  # test passed
            else:
                error = chunk_response.text

        pytest.fail(reason=f"failed to get embedded chunks within {timeout} seconds, potential error: {error}")
