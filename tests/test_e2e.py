import os
import time

import pytest
import requests


def test_upload_to_elastic(file_pdf_path, elasticsearch_storage_handler):
    # clear out
    for chunk in elasticsearch_storage_handler.read_all_items("Chunk"):
        elasticsearch_storage_handler.delete_item(chunk.uuid, "Chunk")

    file_name = os.path.basename(file_pdf_path)
    files = {"file": (file_name, open(file_pdf_path, "rb"), "application/pdf")}
    response = requests.post(url="http://localhost:5002/file", files=files)
    assert response.status_code == 200, response.text

    timeout = 120
    start_time = time.time()

    while time.time() - start_time < timeout:
        for chunk in elasticsearch_storage_handler.read_all_items("Chunk"):
            print(chunk)
            if chunk.embedding:
                return
        time.sleep(1)

    pytest.fail(reason=f"failed to get embedded chunks within {timeout} seconds")
