import os

import pytest

from redbox.storage import FileSystemStorageHandler


def test_file_system_storage_handler(tmp_path):
    """
    Given that `Chunk` is a valid model
    When I initiate FileSystemStorageHandler
    Then I expect a subdirectory called Chunk to exist with the root_path"
    """
    file_system_storage_handler = FileSystemStorageHandler(tmp_path)
    dirs = os.listdir(file_system_storage_handler.root_path)
    assert "Chunk" in dirs


def test_write_item(example_chuck_unsaved, file_system_storage_handler):
    """
    Given that I have an unsaved object
    When I call write_item on it
    Then I expect to see it saved to disk
    """
    file_path = f"{file_system_storage_handler.root_path}/Chunk/{example_chuck_unsaved.uuid}.json"
    assert not os.path.exists(file_path)
    file_system_storage_handler.write_item(example_chuck_unsaved)
    assert os.path.exists(file_path)


def test_delete_item(example_chuck_saved, file_system_storage_handler):
    """
    Given that I have a saved object
    When I call delete_item on it
    Then I expect to see the corresponding file to be deleted
    """
    file_path = (
        f"{file_system_storage_handler.root_path}/Chunk/{example_chuck_saved.uuid}.json"
    )
    assert os.path.exists(file_path)
    file_system_storage_handler.delete_item(example_chuck_saved.uuid, "Chunk")
    assert not os.path.exists(file_path)


def test_delete_item_fail(example_chuck_unsaved, file_system_storage_handler):
    """
    Given that I have an unsaved object
    When I call delete_item on it
    Then I expect to see a FileNotFoundError error raised
    """
    with pytest.raises(FileNotFoundError):
        file_system_storage_handler.delete_item(example_chuck_unsaved.uuid, "Chunk")


def test_delete_items(
    example_chuck_saved, example_chuck_unsaved, file_system_storage_handler
):
    """
    Given that I have both saved and unsaved objects of the same type
    When I call delete_items on their common type-name
    Then I expect to see no error thrown due to the unsaved-missing file
    """
    file_system_storage_handler.delete_items(
        [example_chuck_saved.uuid, example_chuck_unsaved.uuid], "Chunk"
    )


def test_read_item(example_chuck_saved, file_system_storage_handler):
    obj = file_system_storage_handler.read_item(example_chuck_saved.uuid, "Chunk")
    assert obj == example_chuck_saved


def test_read_item_fail(example_chuck_unsaved, file_system_storage_handler):
    """
    Given that I have an unsaved object
    When I call read_item on its uuid
    Then I expect to see a FileNotFoundError error raised
    """
    with pytest.raises(FileNotFoundError):
        file_system_storage_handler.read_item(example_chuck_unsaved.uuid, "Chunk")


def test_read_items(
    example_chuck_saved, example_chuck_unsaved, file_system_storage_handler
):
    """
    Given that I have both saved and unsaved objects
    When I call read_items on their uuids
    Then I expect to see the saved object returned
    And no error to be thrown due the absense of the unsaved object
    """
    objs = file_system_storage_handler.read_items(
        [example_chuck_saved.uuid, example_chuck_unsaved.uuid], "Chunk"
    )
    assert objs == [example_chuck_saved]


def test_list_all_items(
    example_chuck_saved, example_chuck_unsaved, file_system_storage_handler
):
    """
    Given that I have both saved and unsaved objects of the same type
    When I call list_all_items on their common type-name
    Then I expect to see the uuids of the saved objects returned
    """
    uuids = file_system_storage_handler.list_all_items("Chunk")
    assert uuids == [example_chuck_saved.uuid]
