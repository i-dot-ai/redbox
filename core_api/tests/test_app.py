import os

import pytest
from elasticsearch import NotFoundError
from faststream.redis import TestRedisBroker

from core_api.src.app import env, publisher, router
from redbox.models import ProcessingStatusEnum


def test_get_health(app_client):
    """
    Given that the app is running
    When I call /health
    I Expect to see the docs
    """
    response = app_client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_post_file_upload(s3_client, app_client, elasticsearch_storage_handler, file_pdf_path):
    """
    Given a new file
    When I POST it to /file
    I Expect to see it persisted in s3 and elastic-search
    """

    file_name = os.path.basename(file_pdf_path)

    with open(file_pdf_path, "rb") as f:
        async with TestRedisBroker(router.broker):
            response = app_client.post("/file", files={"file": (file_name, f, "pdf")})
    assert response.status_code == 200
    assert s3_client.get_object(
        Bucket=env.bucket_name, Key=file_name
    )
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


def test_delete_file(s3_client, app_client, elasticsearch_storage_handler, chunked_file):
    """
    Given a previously saved file
    When I DELETE it to /file
    I Expect to see it removed from s3 and elastic-search, including the chunks
    """
    # check assets exist
    assert s3_client.get_object(Bucket=env.bucket_name, Key=chunked_file.name)
    assert elasticsearch_storage_handler.read_item(item_uuid=chunked_file.uuid, model_type="file")
    assert elasticsearch_storage_handler.get_file_chunks(chunked_file.uuid)

    response = app_client.delete(f"/file/{chunked_file.uuid}")
    assert response.status_code == 200

    elasticsearch_storage_handler.refresh()

    # check assets dont exist
    with pytest.raises(Exception):
        s3_client.get_object(Bucket=env.bucket_name, Key=chunked_file.name)

    with pytest.raises(NotFoundError):
        elasticsearch_storage_handler.read_item(item_uuid=chunked_file.uuid, model_type="file")

    assert not elasticsearch_storage_handler.get_file_chunks(chunked_file.uuid)


@pytest.mark.asyncio
async def test_ingest_file(app_client, stored_file, elasticsearch_storage_handler):
    """
    Given a previously saved file
    When I POST to /file/uuid/ingest
    I Expect to see a message on the ingester-queue, THIS IS NOT WORKING
    """
    async with TestRedisBroker(router.broker):
        response = app_client.post(f"/file/{stored_file.uuid}/ingest/")

        assert (
            elasticsearch_storage_handler.read_item(
                item_uuid=stored_file.uuid,
                model_type="file",
            ).processing_status
            is ProcessingStatusEnum.parsing
        )
        assert response.status_code == 200

        publisher.mock.called_once_with(stored_file)


def test_read_model(client):
    """
    Given that I have a model in the database
    When I GET /model
    I Expect model-info to be returned
    """
    response = client.get("/model")
    assert response.status_code == 200
    assert response.json() == {
        "max_seq_length": 100,
        "model": env.embedding_model,
        "vector_size": 768,
    }


def test_embed_sentences_422(client):
    """
    Given that I have a model in the database
    When I POST a mall-formed payload to /embedding
    I Expect a 422 error
    """
    response = client.post(
        "/embedding",
        json={"not": "a well formed payload"},
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["msg"] == "Input should be a valid list"


def test_embed_sentences(client):
    """
    Given that I have a model in the database
    When I POST a valid payload consisting of some sentenced to embed to
    /embedding
    I Expect a 200 response

    N.B. We are not testing the content / efficacy of the model in this test.
    """
    response = client.post(
        "/embedding",
        json=["I am the egg man", "I am the walrus"],
    )
    assert response.status_code == 200


def test_get_file_chunks(client, chunked_file):
    response = client.get(f"/file/{chunked_file.uuid}/chunks")
    assert response.status_code == 200
    assert len(response.json()) == 5
