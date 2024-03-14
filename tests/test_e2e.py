import time

import requests

from redbox.storage import ElasticsearchStorageHandler


def test_post_file_upload(file_pdf_path, es_client):
    """
    Given a new file
    When I POST it to /file
    I Expect to see it persisted in s3 and elastic-search
    """

    esh = ElasticsearchStorageHandler(es_client=es_client, root_index="redbox-test-data")
    for item in esh.read_all_items("Chunk"):
        esh.delete_item(item.uuid, model_type="chunk")

    with open(file_pdf_path, "rb") as f:
        response = requests.post("http://localhost:5002/file", files={"file": ("filename", f, "pdf")})
    assert response.status_code == 200

    items = None

    start_time = time.time()
    while not items and time.time() - start_time < 60:
        items = esh.read_all_items("Chunk")

    assert len(items) > 1
