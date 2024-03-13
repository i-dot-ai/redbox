def test_get_health(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_post_file_upload(client):
    response = client.get("/file/upload")
    assert response.status_code == 200


def test_get_file(client, stored_file):
    response = client.get(f"/file/{stored_file.uuid}")
    assert response.status_code == 200


def test_delete_file(client, stored_file):
    response = client.delete(f"/file/{stored_file.uuid}/delete")
    assert response.status_code == 200


def test_ingest_file(client, stored_file):
    response = client.get(f"/file/ingest/{stored_file.uuid}")
    assert response.status_code == 200
