import time
from uuid import uuid4

import pytest
from elastic_transport import ConnectionError
from elasticsearch import NotFoundError

from redbox.models import Chunk
from redbox.storage.elasticsearch import ElasticsearchStorageHandler


def poll_elastic_until_ready(elasticsearch_client):
    """
    Poll the elasticsearch client until it is ready
    """
    time_remainging = 300  # 5 minutes

    while True:
        try:
            elasticsearch_client.ping()
            break
        except ConnectionError:
            pass
        time.sleep(5)
        time_remainging -= 5
        if time_remainging <= 0:
            raise TimeoutError("Elasticsearch client did not become ready in time")

    assert elasticsearch_client.ping()


def test_elasticsearch_client_connection(elasticsearch_client):
    """
    Given that I have a valid Elasticsearch client
    When I call the info method
    Then I expect to see a valid response

    This test is to check all our following elasticsearch tests can proceed.
    """
    conn_test_resp = elasticsearch_client.info()
    assert conn_test_resp["tagline"] == "You Know, for Search"

    test_elasticsearch_storage_handler = ElasticsearchStorageHandler(
        es_client=elasticsearch_client, root_index="redbox-test-data"
    )

    assert isinstance(test_elasticsearch_storage_handler.model_type_map, dict)


def test_elasticsearch_write_read_item(elasticsearch_storage_handler, chunk):
    """
    Given that `Chunk` is a valid model
    When I
    Then I expect a valid Chunk to be returned on read"
    """
    # Write the chunk
    elasticsearch_storage_handler.write_item(item=chunk)

    # Read the chunk
    chunk_read = elasticsearch_storage_handler.read_item(chunk.uuid, "Chunk")

    assert chunk_read.uuid == chunk.uuid


def test_elastic_read_item(elasticsearch_storage_handler, stored_chunk):
    read_chunk = elasticsearch_storage_handler.read_item(stored_chunk.uuid, "Chunk")
    assert read_chunk.uuid == stored_chunk.uuid
    assert read_chunk.parent_file_uuid == stored_chunk.parent_file_uuid
    assert read_chunk.index == stored_chunk.index
    assert read_chunk.text == stored_chunk.text
    assert read_chunk.metadata == stored_chunk.metadata
    assert read_chunk.creator_user_uuid == stored_chunk.creator_user_uuid
    assert read_chunk.token_count == stored_chunk.token_count


def test_elastic_delete_item_fail(
    elasticsearch_storage_handler: ElasticsearchStorageHandler,
):
    """
    Given that I have an non-existent item uuid
    When I call delete_item on it
    Then I expect to see a NotFoundError error raised
    """
    with pytest.raises(NotFoundError):
        elasticsearch_storage_handler.delete_item(uuid4(), "Chunk")


def test_elastic_read_item_fail(
    elasticsearch_storage_handler: ElasticsearchStorageHandler,
):
    """
    Given that I have an non-existent item uuid
    When I call read_item on its uuid
    Then I expect to see a NotFoundError error raised
    """
    with pytest.raises(NotFoundError):
        elasticsearch_storage_handler.read_item(uuid4(), "Chunk")


def test_elastic_write_read_delete_items(elasticsearch_storage_handler):
    """
    Given that I have a list of items
    When I call write_items on them
    Then I expect to see them written to the database
    """
    chunks = [
        Chunk(
            parent_file_uuid=uuid4(),
            index=i,
            text="test_text",
            metadata={},
        )
        for i in range(10)
    ]

    elasticsearch_storage_handler.write_items(chunks)

    read_chunks = elasticsearch_storage_handler.read_items(
        [chunk.uuid for chunk in chunks], "Chunk"
    )

    assert read_chunks == chunks

    chunk_uuids_to_delete = [chunk.uuid for chunk in chunks]
    # Delete the chunks
    elasticsearch_storage_handler.delete_items(chunk_uuids_to_delete, "Chunk")

    # Check that the chunks are deleted
    items_left = elasticsearch_storage_handler.list_all_items("Chunk")
    assert chunk_uuids_to_delete not in items_left


@pytest.mark.xfail(reason="")
def test_list_all_items(
    elasticsearch_storage_handler: ElasticsearchStorageHandler, chunk: Chunk
):
    """
    Given that I have both saved and unsaved objects of the same type
    When I call list_all_items on their common type-name
    Then I expect to see the uuids of the saved objects returned
    """
    uuids = elasticsearch_storage_handler.list_all_items("Chunk")
    assert len(uuids) > 0


def test_elastic_delete_item(elasticsearch_storage_handler, stored_chunk):
    """
    Given that I have a saved object
    When I call delete_item on it
    Then I expect to not be able to read the item
    """
    elasticsearch_storage_handler.delete_item(stored_chunk.uuid, "Chunk")

    with pytest.raises(NotFoundError):
        elasticsearch_storage_handler.read_item(stored_chunk.uuid, "Chunk")


def test_get_file_status_complete(elasticsearch_storage_handler, file):
    """
    Given that `File` is a valid model
    When I call get_file_status on a file with complete processing status
    Then I expect to see the file's UUID and processing status returned
    """
    file.processing_status = "complete"
    elasticsearch_storage_handler.update_item(file.uuid, file)

    status_body = elasticsearch_storage_handler.get_file_status(file.uuid)

    assert status_body["uuid"] == file.uuid
    assert status_body["processing_status"] == "complete"


def test_get_file_status_incomplete(elasticsearch_storage_handler, file):
    """
    Given that `File` is a valid model
    When I call get_file_status on a file with incomplete processing status
    Then I expect to see the file's UUID and processing status returned
    """
    file.processing_status = "embedding"
    elasticsearch_storage_handler.update_item(file.uuid, file)

    status_body = elasticsearch_storage_handler.get_file_status(file.uuid)

    assert status_body["uuid"] == file.uuid
    assert status_body["processing_status"] == "embedding"


def test_get_file_status_all_chunks_embedded(elasticsearch_storage_handler, file):
    """
    Given that `File` is a valid model
    When I call get_file_status on a file with all chunks embedded
    Then I expect the file's processing status to be updated to "complete"
    """
    file.processing_status = "embedding"
    elasticsearch_storage_handler.update_item(file.uuid, file)

    chunk_count = 10
    embedded_chunk_count = 10
    elasticsearch_storage_handler._count_chunks = lambda file_uuid: chunk_count
    elasticsearch_storage_handler._count_embedded_chunks = (
        lambda file_uuid: embedded_chunk_count
    )

    status_body = elasticsearch_storage_handler.get_file_status(file.uuid)

    assert status_body["uuid"] == file.uuid
    assert status_body["processing_status"] == "complete"

    updated_file = elasticsearch_storage_handler.read_item(file.uuid, "File")
    assert updated_file.processing_status == "complete"


def test_get_file_status_partial_chunks_embedded(elasticsearch_storage_handler, file):
    """
    Given that `File` is a valid model
    When I call get_file_status on a file with partial chunks embedded
    Then I expect the file's processing status to remain unchanged
    """
    file.processing_status = "embedding"
    elasticsearch_storage_handler.update_item(file.uuid, file)

    chunk_count = 10
    embedded_chunk_count = 5
    elasticsearch_storage_handler._count_chunks = lambda file_uuid: chunk_count
    elasticsearch_storage_handler._count_embedded_chunks = (
        lambda file_uuid: embedded_chunk_count
    )

    status_body = elasticsearch_storage_handler.get_file_status(file.uuid)

    assert status_body["uuid"] == file.uuid
    assert status_body["processing_status"] == "embedding"

    updated_file = elasticsearch_storage_handler.read_item(file.uuid, "File")
    assert updated_file.processing_status == "embedding"
