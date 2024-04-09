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

        authenticated_s3_url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket_name, "Key": file_key},
            ExpiresIn=3600,
        )

        response = requests.post(
            url="http://localhost:5002/file",
            params={
                "name": "filename",
                "type": ".pdf",
                "location": authenticated_s3_url,
            },
        )
        assert response.status_code == 200
        file_uuid = response.json()

        timeout = 120  # 10s should be plenty
        start_time = time.time()
        embeddings_found = False
        error = ""

        while not embeddings_found and time.time() - start_time < timeout:
            time.sleep(1)
            chunk_response = requests.get(f"http://localhost:5002/file/{file_uuid}/chunks")
            if chunk_response.status_code == 200:
                embeddings_found = any(chunk["embedding"] for chunk in chunk_response.json())
            else:
                error = chunk_response.text

        if not embeddings_found:
            pytest.fail(reason=f"failed to get embedded chunks within {timeout} seconds, potential error: {error}")
