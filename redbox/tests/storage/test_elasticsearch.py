from uuid import uuid4, UUID

import pytest
from elasticsearch import NotFoundError

from redbox.models import Chunk
from redbox.storage.elasticsearch import ElasticsearchStorageHandler


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


def test_elasticsearch_write_read_item(elasticsearch_storage_handler, chunk_belonging_to_alice):
    """
    Given that `Chunk` is a valid model
    When I
    Then I expect a valid Chunk to be returned on read"
    """
    # Write the chunk
    elasticsearch_storage_handler.write_item(item=chunk_belonging_to_alice)

    # Read the chunk
    chunk_read = elasticsearch_storage_handler.read_item(chunk_belonging_to_alice.uuid, "Chunk")

    assert chunk_read.uuid == chunk_belonging_to_alice.uuid


def test_elastic_read_item(elasticsearch_storage_handler, stored_chunk_belonging_to_alice):
    read_chunk = elasticsearch_storage_handler.read_item(stored_chunk_belonging_to_alice.uuid, "Chunk")
    assert read_chunk.uuid == stored_chunk_belonging_to_alice.uuid
    assert read_chunk.parent_file_uuid == stored_chunk_belonging_to_alice.parent_file_uuid
    assert read_chunk.index == stored_chunk_belonging_to_alice.index
    assert read_chunk.text == stored_chunk_belonging_to_alice.text
    assert read_chunk.metadata == stored_chunk_belonging_to_alice.metadata
    assert read_chunk.creator_user_uuid == stored_chunk_belonging_to_alice.creator_user_uuid
    assert read_chunk.token_count == stored_chunk_belonging_to_alice.token_count


def test_elastic_delete_item_fail(
    elasticsearch_storage_handler: ElasticsearchStorageHandler,
    chunk_belonging_to_bob,
):
    """
    Given that I have an non-existent item uuid
    When I call delete_item on it
    Then I expect to see a NotFoundError error raised
    """
    with pytest.raises(NotFoundError):
        elasticsearch_storage_handler.delete_item(chunk_belonging_to_bob)


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
    creator_user_uuid = uuid4()
    chunks = [
        Chunk(
            creator_user_uuid=creator_user_uuid,
            parent_file_uuid=uuid4(),
            index=i,
            text="test_text",
            metadata={},
        )
        for i in range(10)
    ]

    elasticsearch_storage_handler.write_items(chunks)

    read_chunks = elasticsearch_storage_handler.read_items([chunk.uuid for chunk in chunks], "Chunk")

    assert read_chunks == chunks

    # Delete the chunks
    elasticsearch_storage_handler.delete_items(chunks)

    # Check that the chunks are deleted
    items_left = elasticsearch_storage_handler.list_all_items("Chunk", creator_user_uuid)

    assert all(chunk.uuid not in items_left for chunk in chunks)


def test_list_all_items(
    elasticsearch_storage_handler: ElasticsearchStorageHandler,
    stored_chunk_belonging_to_alice: Chunk,
    stored_chunk_belonging_to_bob: Chunk,
    chunk_belonging_to_claire: Chunk,
    alice: UUID,
):
    """
    Given that I have
    * a saved chunk belonging to Alice
    * a saved chunk belonging to Bob
    * an unsaved chunk belonging to Claire
    When I call list_all_items as alice
    Then I expect to see the uuids of the saved objects that belong to alice returned
    """
    uuids = elasticsearch_storage_handler.list_all_items("Chunk", alice)
    assert len(uuids) == 1


def test_read_all_items(
    elasticsearch_storage_handler: ElasticsearchStorageHandler,
    stored_chunk_belonging_to_alice: Chunk,
    stored_chunk_belonging_to_bob: Chunk,
    chunk_belonging_to_claire: Chunk,
    alice: UUID,
):
    """
    Given that I have
    * a saved chunk belonging to Alice
    * a saved chunk belonging to Bob
    * an unsaved chunk belonging to Claire
    When I call read_all_items as alice
    Then I expect to see the one Chunk belonging to alice
    """
    chunks = elasticsearch_storage_handler.read_all_items("Chunk", alice)
    assert len(chunks) == 1
    assert chunks[0].creator_user_uuid == alice


def test_elastic_delete_item(elasticsearch_storage_handler, stored_chunk_belonging_to_alice):
    """
    Given that I have a saved object
    When I call delete_item on it
    Then I expect to not be able to read the item
    """
    elasticsearch_storage_handler.delete_item(stored_chunk_belonging_to_alice)

    with pytest.raises(NotFoundError):
        elasticsearch_storage_handler.read_item(stored_chunk_belonging_to_alice.uuid, "Chunk")


def test_get_file_chunks(
    elasticsearch_storage_handler: ElasticsearchStorageHandler,
    stored_chunk_belonging_to_alice: Chunk,
):
    """
    Given that a chunk belonging to a file belonging alice have been saved
    When I call get_file_chunks with the right file id and alice's id
    I Expect the single chunk to be retrieved
    """
    assert stored_chunk_belonging_to_alice.creator_user_uuid

    chunks = elasticsearch_storage_handler.get_file_chunks(
        stored_chunk_belonging_to_alice.parent_file_uuid,
        stored_chunk_belonging_to_alice.creator_user_uuid,
    )

    assert len(chunks) == 1


def test_get_file_chunks_fail(
    elasticsearch_storage_handler: ElasticsearchStorageHandler,
    stored_chunk_belonging_to_alice: Chunk,
):
    """
    Given that a chunk belonging to a file belonging alice have been saved
    When I call get_file_chunks with the right file id and another id
    I Expect the no chunks to be retrieved
    """
    other_chunks = elasticsearch_storage_handler.get_file_chunks(
        stored_chunk_belonging_to_alice.parent_file_uuid,
        uuid4(),
    )
    assert not other_chunks
