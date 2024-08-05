from uuid import UUID, uuid4

import pytest
from elasticsearch import NotFoundError

from redbox.models import File
from redbox.storage.elasticsearch import ElasticsearchStorageHandler


def test_elasticsearch_client_connection(elasticsearch_client, elasticsearch_storage_handler):
    """
    Given that I have a valid Elasticsearch client
    When I call the info method
    Then I expect to see a valid response

    This test is to check all our following elasticsearch tests can proceed.
    """
    conn_test_resp = elasticsearch_client.info()
    assert conn_test_resp["tagline"] == "You Know, for Search"

    assert isinstance(elasticsearch_storage_handler.model_type_map, dict)


def test_elasticsearch_write_read_item(elasticsearch_storage_handler, file_belonging_to_alice):
    """
    Given that `File` is a valid model
    When I
    Then I expect a valid File to be returned on read"
    """
    # Write the file
    elasticsearch_storage_handler.write_item(item=file_belonging_to_alice)

    # Read the File
    item_read = elasticsearch_storage_handler.read_item(file_belonging_to_alice.uuid, "File")

    assert item_read.uuid == file_belonging_to_alice.uuid


def test_elastic_delete_item_fail(
    elasticsearch_storage_handler: ElasticsearchStorageHandler,
):
    """
    Given that I have an non-existent item uuid
    When I call delete_item on it
    Then I expect to see a NotFoundError error raised
    """
    with pytest.raises(NotFoundError):
        elasticsearch_storage_handler.delete_item(File(uuid=uuid4(), creator_user_uuid=uuid4(), key="", bucket=""))


def test_elastic_read_item_fail(
    elasticsearch_storage_handler: ElasticsearchStorageHandler,
):
    """
    Given that I have an non-existent item uuid
    When I call read_item on its uuid
    Then I expect to see a NotFoundError error raised
    """
    with pytest.raises(NotFoundError):
        elasticsearch_storage_handler.read_item(uuid4(), "File")


def test_elastic_write_read_delete_items(elasticsearch_storage_handler):
    """
    Given that I have a list of items
    When I call write_items on them
    Then I expect to see them written to the database
    """
    creator_user_uuid = uuid4()
    files = [File(creator_user_uuid=creator_user_uuid, key=f"somefile-{i}.txt", bucket="a-bucket") for i in range(10)]

    elasticsearch_storage_handler.write_items(files)

    read_files = elasticsearch_storage_handler.read_items([file.uuid for file in files], "File")

    assert read_files == files

    # Delete the files
    elasticsearch_storage_handler.delete_items(files)

    # Check that the files are deleted
    items_left = elasticsearch_storage_handler.list_all_items("File", creator_user_uuid)

    assert all(file.uuid not in items_left for file in files)


def test_list_all_items(
    elasticsearch_storage_handler: ElasticsearchStorageHandler,
    file_belonging_to_alice: File,
    file_belonging_to_bob: File,
    alice: UUID,
):
    """
    Given that I have
    * a saved file belonging to Alice
    * a saved file belonging to Bob
    When I call list_all_items as alice
    Then I expect to see the uuids of the saved objects that belong to alice returned
    """
    uuids = elasticsearch_storage_handler.list_all_items("File", alice)
    assert len(uuids) == 1, f"Unexpected number of files {len(uuids)}"


def test_read_all_items(
    elasticsearch_storage_handler: ElasticsearchStorageHandler,
    file_belonging_to_alice: File,
    file_belonging_to_bob: File,
    alice: UUID,
):
    """
    Given that I have
    * a saved file belonging to Alice
    * a saved file belonging to Bob
    When I call read_all_items as alice
    Then I expect to see the one File belonging to alice
    """
    files = elasticsearch_storage_handler.read_all_items("File", alice)
    assert len(files) == 1
    assert files[0].creator_user_uuid == alice


def test_elastic_delete_item(elasticsearch_storage_handler, file_belonging_to_alice):
    """
    Given that I have a saved object
    When I call delete_item on it
    Then I expect to not be able to read the item
    """
    elasticsearch_storage_handler.delete_item(file_belonging_to_alice)

    with pytest.raises(NotFoundError):
        elasticsearch_storage_handler.read_item(file_belonging_to_alice.uuid, "File")


def test_elastic_delete_user_item(elasticsearch_storage_handler, file_belonging_to_alice, alice):
    """
    Given that I have a saved object
    When I call delete_item on it
    Then I expect to not be able to read the item
    """
    files = elasticsearch_storage_handler.read_all_items("File", alice)
    assert len(files) == 1
    assert files[0].creator_user_uuid == alice

    elasticsearch_storage_handler.delete_user_items("file", alice)
    elasticsearch_storage_handler.refresh()
    files = elasticsearch_storage_handler.read_all_items("File", alice)
    assert len(files) == 0
