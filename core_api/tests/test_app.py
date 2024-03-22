import json

import pytest
from elasticsearch import NotFoundError

from core_api.src.app import env
from redbox.models import ProcessingStatusEnum


def test_get_health(app_client):
    """
    Given that the app is running
    When I call /health
    I Expect to see the docs
    """
    response = app_client.get("/health")
    assert response.status_code == 200


def test_post_file_upload(s3_client, app_client, elasticsearch_storage_handler, bucket, file_pdf_path):
    """
    Given a new file
    When I POST it to /file
    I Expect to see it persisted in s3 and elastic-search
    """
    with open(file_pdf_path, "rb") as f:
        response = app_client.post("/file", files={"file": ("filename", f, "pdf")})
    assert response.status_code == 200
    assert s3_client.get_object(Bucket=bucket, Key=file_pdf_path.split("/")[-1])
    json_response = response.json()
    assert (
        elasticsearch_storage_handler.read_item(
            item_uuid=json_response["uuid"],
            model_type=json_response["model_type"],
        ).processing_status
        is ProcessingStatusEnum.parsing
    )


def test_get_file(app_client, stored_file):
    """
    Given a previously saved file
    When I GET it from /file/uuid
    I Expect to receive it
    """

    response = app_client.get(f"/file/{stored_file.uuid}")
    assert response.status_code == 200


def test_delete_file(s3_client, app_client, elasticsearch_storage_handler, bucket, stored_file):
    """
    Given a previously saved file
    When I DELETE it to /file
    I Expect to see it removed from s3 and elastic-search
    """
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


def test_ingest_file(app_client, rabbitmq_channel, stored_file, elasticsearch_storage_handler):
    """
    Given a previously saved file
    When I POST to /file/uuid/ingest
    I Expect to see a message on the ingest-queue, THIS IS NOT WORKING
    """
    response = app_client.post(f"/file/{stored_file.uuid}/ingest/")

    assert (
        elasticsearch_storage_handler.read_item(
            item_uuid=stored_file.uuid,
            model_type="file",
        ).processing_status
        is ProcessingStatusEnum.parsing
    )
    assert response.status_code == 200

    method, _properties, body = rabbitmq_channel.basic_get(env.ingest_queue_name)
    msg = json.loads(body.decode())
    assert msg["text_hash"] == response.json()["text_hash"]


def test_read_all_models(client):
    """
    Given that I have one model, in the database
    When I GET all models /models
    I Expect a list of just one model to be returned
    """
    response = client.get("/models")
    assert response.status_code == 200
    assert response.json() == {
        "models": [
            {
                "max_seq_length": 100,
                "model": env.embedding_model,
                "vector_size": 768,
            }
        ]
    }


def test_read_one_model(client):
    """
    Given that I have one model in the database
    When I GET this one model /models/<name>
    I Expect a single model to be returned
    """
    response = client.get(f"/models/{env.embedding_model}")
    assert response.status_code == 200
    assert response.json() == {
        "max_seq_length": 100,
        "model": env.embedding_model,
        "vector_size": 768,
    }


def test_read_models_404(client):
    """
    Given that I have one model in the database
    When I GET a non-existent model /models/not-a-model
    I Expect a 404 error
    """
    response = client.get("/models/not-a-model")
    assert response.status_code == 404
    assert response.json() == {"detail": "Model not-a-model not found"}


def test_embed_sentences_422(client):
    """
    Given that I have one model in the database
    When I POST a mall-formed payload to /models/<model-name>/embed
    I Expect a 422 error
    """
    response = client.post(
        f"/models/{env.embedding_model}/embed",
        json={"not": "a well formed payload"},
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["msg"] == "Input should be a valid list"


def test_embed_sentences(client):
    """
    Given that I have one model in the database
    When I POST a valid payload consisting of some sentenced to embed to
    /models/<model-name>/embed
    I Expect a 200 response

    N.B. We are not testing the content / efficacy of the model in this test.
    """
    response = client.post(
        f"/models/{env.embedding_model}/embed",
        json=["I am the egg man", "I am the walrus"],
    )
    assert response.status_code == 200
