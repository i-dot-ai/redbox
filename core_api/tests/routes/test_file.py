import os

import pytest
from elasticsearch import NotFoundError
from faststream.redis import TestRedisBroker

from core_api.src.routes.file import env, router


@pytest.mark.asyncio
async def test_post_file_upload(s3_client, app_client, elasticsearch_storage_handler, file_pdf_path, headers):
    """
    Given a new file
    When I POST it to /file
    I Expect to see it persisted in elastic-search
    """

    file_key = os.path.basename(file_pdf_path)

    with open(file_pdf_path, "rb") as f:
        s3_client.upload_fileobj(
            Bucket=env.bucket_name,
            Fileobj=f,
            Key=file_key,
            ExtraArgs={"Tagging": "file_type=pdf"},
        )

        async with TestRedisBroker(router.broker):
            response = app_client.post(
                "/file",
                json={
                    "key": file_key,
                    "bucket": env.bucket_name,
                },
                headers=headers,
            )
    assert response.status_code == 201


def test_get_file(app_client, stored_file, headers):
    """
    Given a previously saved file
    When I GET it from /file/uuid
    I Expect to receive it
    """
    response = app_client.get(f"/file/{stored_file.uuid}", headers=headers)
    assert response.status_code == 200


def test_delete_file(s3_client, app_client, elasticsearch_storage_handler, chunked_file, headers):
    """
    Given a previously saved file
    When I DELETE it to /file
    I Expect to see it removed from s3 and elastic-search, including the chunks
    """
    # check assets exist
    assert s3_client.get_object(Bucket=env.bucket_name, Key=chunked_file.key)
    assert elasticsearch_storage_handler.read_item(item_uuid=chunked_file.uuid, model_type="file")
    assert elasticsearch_storage_handler.get_file_chunks(chunked_file.uuid, chunked_file.creator_user_uuid)

    response = app_client.delete(f"/file/{chunked_file.uuid}", headers=headers)
    assert response.status_code == 200

    elasticsearch_storage_handler.refresh()

    # check assets dont exist
    with pytest.raises(s3_client.exceptions.NoSuchKey):
        s3_client.get_object(Bucket=env.bucket_name, Key=chunked_file.key)

    with pytest.raises(NotFoundError):
        elasticsearch_storage_handler.read_item(item_uuid=chunked_file.uuid, model_type="file")

    assert not elasticsearch_storage_handler.get_file_chunks(chunked_file.uuid, chunked_file.creator_user_uuid)


def test_get_file_chunks(client, chunked_file, headers):
    response = client.get(f"/file/{chunked_file.uuid}/chunks", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 5
