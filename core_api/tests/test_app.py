def test_get_health(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_post_file_upload(client, bucket, file_pdf_path, file):
    with open(file_pdf_path, "rb") as f:
        response = client.post("/file", files={"file": ("filename", f, "pdf")})
    assert response.status_code == 200


def test_get_file(client, stored_file):
    response = client.get(f"/file/{stored_file.uuid}")
    assert response.status_code == 200


def test_delete_file(client, stored_file):
    response = client.delete(f"/file/{stored_file.uuid}")
    assert response.status_code == 200


def test_ingest_file(client, stored_file):
    response = client.post(f"/file/{stored_file.uuid}/ingest/")
    assert response.status_code == 200
