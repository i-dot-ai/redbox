import os
import time

import pytest
import requests


def test_upload_to_elastic(file_pdf_path):
    """
    When I POST a file to core-api/file
    I Expect a Chunk with a non-null embedding ... eventually
    """

    file_name = os.path.basename(file_pdf_path)
    files = {"file": (file_name, open(file_pdf_path, "rb"), "application/pdf")}
    response = requests.post(url="http://localhost:5002/file", files=files)
    assert response.status_code == 200
    file_uuid = response.json()["uuid"]

    timeout = 60  # 10s should be plenty
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
