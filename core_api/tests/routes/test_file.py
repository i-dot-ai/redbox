import os

import pytest
from elasticsearch import NotFoundError
from faststream.redis import TestRedisBroker

from core_api.src.routes.file import env, router


@pytest.mark.asyncio
async def test_post_file_upload(
    s3_client, app_client, elasticsearch_storage_handler, file_pdf_path
):
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

        authenticated_s3_url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": env.bucket_name, "Key": file_key},
            ExpiresIn=3600,
        )

        async with TestRedisBroker(router.broker):
            response = app_client.post(
                "/file",
                params={
                    "name": "filename",
                    "type": ".pdf",
                    "location": authenticated_s3_url,
                },
            )
    assert response.status_code == 200


def test_get_file(app_client, stored_file):
    """
    Given a previously saved file
    When I GET it from /file/uuid
    I Expect to receive it
    """

    response = app_client.get(f"/file/{stored_file.uuid}")
    assert response.status_code == 200


def test_delete_file(
    s3_client, app_client, elasticsearch_storage_handler, chunked_file
):
    """
    Given a previously saved file
    When I DELETE it to /file
    I Expect to see it removed from s3 and elastic-search, including the chunks
    """
    # check assets exist
    assert s3_client.get_object(Bucket=env.bucket_name, Key=chunked_file.name)
    assert elasticsearch_storage_handler.read_item(
        item_uuid=chunked_file.uuid, model_type="file"
    )
    assert elasticsearch_storage_handler.get_file_chunks(chunked_file.uuid)

    response = app_client.delete(f"/file/{chunked_file.uuid}")
    assert response.status_code == 200

    elasticsearch_storage_handler.refresh()

    # check assets dont exist
    with pytest.raises(Exception):
        s3_client.get_object(Bucket=env.bucket_name, Key=chunked_file.name)

    with pytest.raises(NotFoundError):
        elasticsearch_storage_handler.read_item(
            item_uuid=chunked_file.uuid, model_type="file"
        )

    assert not elasticsearch_storage_handler.get_file_chunks(chunked_file.uuid)


def test_get_file_chunks(client, chunked_file):
    response = client.get(f"/file/{chunked_file.uuid}/chunks")
    assert response.status_code == 200
    assert len(response.json()) == 5
