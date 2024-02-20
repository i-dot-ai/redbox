import pytest
from elasticsearch import NotFoundError

from redbox.models import Chunk
from redbox.storage.elasticsearch import ElasticsearchStorageHandler


@pytest.mark.usefixtures("elasticsearch_client")
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


@pytest.mark.usefixtures("elasticsearch_storage_handler", "chunk")
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


@pytest.mark.usefixtures("elasticsearch_storage_handler", "chunk")
def test_elastic_read_item(elasticsearch_storage_handler, chunk):
    read_chunk = elasticsearch_storage_handler.read_item(chunk.uuid, "Chunk")
    assert read_chunk.uuid == chunk.uuid
    assert read_chunk.parent_file_uuid == chunk.parent_file_uuid
    assert read_chunk.index == chunk.index
    assert read_chunk.text == chunk.text
    assert read_chunk.metadata == chunk.metadata
    assert read_chunk.creator_user_uuid == chunk.creator_user_uuid
    assert read_chunk.token_count == chunk.token_count


@pytest.mark.usefixtures("elasticsearch_storage_handler", "chunk")
def test_elastic_delete_item_fail(
    elasticsearch_storage_handler: ElasticsearchStorageHandler,
):
    """
    Given that I have an non-existent item uuid
    When I call delete_item on it
    Then I expect to see a NotFoundError error raised
    """
    with pytest.raises(NotFoundError):
        elasticsearch_storage_handler.delete_item("bad-uuid", "Chunk")


@pytest.mark.usefixtures("elasticsearch_storage_handler")
def test_elastic_read_item_fail(
    elasticsearch_storage_handler: ElasticsearchStorageHandler,
):
    """
    Given that I have an non-existent item uuid
    When I call read_item on its uuid
    Then I expect to see a NotFoundError error raised
    """
    with pytest.raises(NotFoundError):
        elasticsearch_storage_handler.read_item("bad-uuid", "Chunk")


@pytest.mark.usefixtures("elasticsearch_storage_handler")
def test_elastic_write_read_delete_items(elasticsearch_storage_handler):
    """
    Given that I have a list of items
    When I call write_items on them
    Then I expect to see them written to the database
    """
    chunks = []
    for i in range(0, 10):
        chunks.append(
            Chunk(
                parent_file_uuid="test_uuid",
                index=i,
                text="test_text",
                metadata={},
                creator_user_uuid="test",
            )
        )

    elasticsearch_storage_handler.write_items(chunks)

    read_chunks = elasticsearch_storage_handler.read_items(
        [chunk.uuid for chunk in chunks], "Chunk"
    )

    for i, chunk in enumerate(read_chunks):
        assert chunk.uuid == chunks[i].uuid
        assert chunk.parent_file_uuid == chunks[i].parent_file_uuid
        assert chunk.index == chunks[i].index
        assert chunk.text == chunks[i].text
        assert chunk.metadata == chunks[i].metadata
        assert chunk.creator_user_uuid == chunks[i].creator_user_uuid
        assert chunk.token_count == chunks[i].token_count

    # Delete the chunks
    elasticsearch_storage_handler.delete_items(
        [chunk.uuid for chunk in chunks], "Chunk"
    )

    # Check that the chunks are deleted
    for chunk in chunks:
        with pytest.raises(NotFoundError):
            elasticsearch_storage_handler.read_item(chunk.uuid, "Chunk")


@pytest.mark.usefixtures("elasticsearch_storage_handler", "chunk")
def test_list_all_items(
    elasticsearch_storage_handler: ElasticsearchStorageHandler, chunk: Chunk
):
    """
    Given that I have both saved and unsaved objects of the same type
    When I call list_all_items on their common type-name
    Then I expect to see the uuids of the saved objects returned
    """
    uuids = elasticsearch_storage_handler.list_all_items("Chunk")
    assert chunk.uuid in uuids


@pytest.mark.usefixtures("elasticsearch_storage_handler", "chunk")
def test_elastic_delete_item(elasticsearch_storage_handler, chunk):
    """
    Given that I have a saved object
    When I call delete_item on it
    Then I expect to not be able to read the item
    """
    elasticsearch_storage_handler.delete_item(chunk.uuid, "Chunk")

    with pytest.raises(NotFoundError):
        elasticsearch_storage_handler.read_item(chunk.uuid, "Chunk")
