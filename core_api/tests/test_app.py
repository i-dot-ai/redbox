import pytest
from elasticsearch import NotFoundError


def test_get_health(app_client):
    response = app_client.get("/health")
    assert response.status_code == 200


def test_post_file_upload(s3_client, app_client, elasticsearch_storage_handler, bucket, file_pdf_path):
    with open(file_pdf_path, "rb") as f:
        response = app_client.post("/file", files={"file": ("filename", f, "pdf")})
    assert response.status_code == 200
    assert s3_client.get_object(Bucket=bucket, Key=file_pdf_path.split("/")[-1])
    json_response = response.json()
    assert elasticsearch_storage_handler.read_item(
        item_uuid=json_response["uuid"], model_type=json_response["model_type"]
    )


def test_get_file(app_client, stored_file):
    response = app_client.get(f"/file/{stored_file.uuid}")
    assert response.status_code == 200


def test_delete_file(s3_client, app_client, elasticsearch_storage_handler, bucket, stored_file):
    # check assets exist
    assert s3_client.get_object(Bucket=bucket, Key=stored_file.name)
    assert elasticsearch_storage_handler.read_item(item_uuid=stored_file.uuid, model_type="file")

    response = app_client.delete(f"/file/{stored_file.uuid}")
    assert response.status_code == 200

    # check assets dont exist
    with pytest.raises(Exception):
        s3_client.get_object(Bucket=bucket, Key=stored_file.name)

    with pytest.raises(NotFoundError):
        elasticsearch_storage_handler.read_item(item_uuid=stored_file.uuid, model_type="file")


def test_ingest_file(app_client, stored_file):
    response = app_client.post(f"/file/{stored_file.uuid}/ingest/")
    assert response.status_code == 200
    # TODO: check that message is in queue
