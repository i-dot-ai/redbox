import json
from http import HTTPStatus
from pathlib import Path
from jose import jwt

import pytest
from elasticsearch import NotFoundError
from faststream.redis import TestRedisBroker

from core_api.routes.file import env, router
from redbox.storage.elasticsearch import ElasticsearchStorageHandler

@pytest.mark.asyncio()
async def test_post_file_upload(app_client, file_pdf_path: Path, headers):
    """
    Given a new file
    When I POST it to /file
    I Expect to see it persisted in elastic-search
    """

    file_key = file_pdf_path.name

    with file_pdf_path.open("rb") as f:

        async with TestRedisBroker(router.broker):
            response = app_client.post(
                "/file",
                json={
                    "key": file_key,
                    "bucket": env.bucket_name,
                },
                headers=headers,
            )
    assert response.status_code == HTTPStatus.CREATED

    file = json.loads(response.content.decode("utf-8"))
    assert file["ingest_status"] == "processing"


def test_list_files(app_client, stored_file_1, headers):
    """
    Given a previously saved file
    When I GET all files from /file
    I Expect the response to contain this file
    """
    response = app_client.get("/file", headers=headers)
    assert response.status_code == HTTPStatus.OK

    file_list = json.loads(response.content.decode("utf-8"))
    assert len(file_list) > 0

    assert str(stored_file_1.uuid) in [file["uuid"] for file in file_list]


def test_get_file(app_client, stored_file_1, headers):
    """
    Given a previously saved file
    When I GET it from /file/uuid
    I Expect to receive it
    """
    response = app_client.get(f"/file/{stored_file_1.uuid}", headers=headers)
    assert response.status_code == HTTPStatus.OK


def test_get_missing_file(app_client, headers):
    """
    Given a nonexistent file
    When I GET it from /file/uuid
    I Expect to receive a 404 error
    """
    response = app_client.get("/file/ffffffff-ffff-ffff-ffff-ffffffffffff", headers=headers)
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_delete_file(app_client, elasticsearch_storage_handler, chunked_file, headers):
    """
    Given a previously saved file
    When I DELETE it to /file
    I Expect to see it removed from s3 and elastic-search, including the chunks
    """
    # check assets exist
    assert elasticsearch_storage_handler.read_item(item_uuid=chunked_file.uuid, model_type="file")
    assert elasticsearch_storage_handler.list_all_items("chunk", chunked_file.creator_user_uuid)

    response = app_client.delete(f"/file/{chunked_file.uuid}", headers=headers)
    assert response.status_code == HTTPStatus.OK

    elasticsearch_storage_handler.refresh()

    # check assets dont exist

    with pytest.raises(NotFoundError):
        elasticsearch_storage_handler.read_item(item_uuid=chunked_file.uuid, model_type="file")

    assert not elasticsearch_storage_handler.list_all_items("chunk", chunked_file.creator_user_uuid)


def test_delete_missing_file(app_client, headers):
    """
    Given a nonexistent file
    When I DELETE it to /file
    I Expect to receive a 404 error
    """
    response = app_client.delete("/file/ffffffff-ffff-ffff-ffff-ffffffffffff", headers=headers)
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_reingest_file(app_client, chunked_user_files, stored_user_files, elasticsearch_storage_handler):
    """
    Given a previously chunked file
    When I PUT it to /file/uuid/
    I Expect the old chunks to be removed
    """
    test_file = stored_user_files[0]

    bearer_token = jwt.encode({"user_uuid": str(test_file.creator_user_uuid)}, key="nvjkernd")
    headers_for_user = {"Authorization": f"Bearer {bearer_token}"}

    previous_chunks_by_file = [
        elasticsearch_storage_handler.list_all_items(
            "chunk", 
            file.creator_user_uuid, 
            filters=[ElasticsearchStorageHandler.get_with_parent_file_filter(file.uuid)]
        )
        for file in stored_user_files 
    ]

    response = app_client.put(f"/file/{test_file.uuid}", headers=headers_for_user)
    assert response.status_code == HTTPStatus.OK, f"Error response: [{response.status_code}] {response.text}"

    elasticsearch_storage_handler.refresh()
    assert (
        elasticsearch_storage_handler.list_all_items("chunk", test_file.creator_user_uuid) != previous_chunks_by_file[0]
    ), f"Pre and post chunks matched and both had {len(previous_chunks_by_file[0])} chunks"

    for file, previous_chunks in zip(stored_user_files[1:], previous_chunks_by_file[1:]):
        post_chunks = elasticsearch_storage_handler.list_all_items("chunk", file.creator_user_uuid)
        assert post_chunks == previous_chunks, f"Additional files had their chunks changed! Pre: {len(previous_chunks)} Post: {len(post_chunks)}"


def test_get_missing_file_chunks(app_client, headers):
    """
    Given a nonexistent file
    When I GET it from /file/uuid/chunks
    I Expect to receive a 404 error
    """
    response = app_client.get("/file/ffffffff-ffff-ffff-ffff-ffffffffffff/chunks", headers=headers)
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_get_missing_file_status(app_client, headers):
    """
    Given a nonexistent file
    When I GET it from /file/uuid/status
    I Expect to receive a 404 error
    """
    response = app_client.get("/file/ffffffff-ffff-ffff-ffff-ffffffffffff/status", headers=headers)
    assert response.status_code == HTTPStatus.NOT_FOUND
