from uuid import uuid4

import pytest

from redbox.models import Chunk
from redbox.storage import FileSystemStorageHandler


@pytest.fixture
def file_system_storage_handler(tmp_path) -> FileSystemStorageHandler:
    yield FileSystemStorageHandler(tmp_path)


@pytest.fixture
def chunk() -> Chunk:
    chunk = Chunk(
        parent_file_uuid="test_uuid",
        index=1,
        text="test_text",
        metadata={},
        creator_user_uuid="test",
    )
    yield chunk


@pytest.fixture
def example_chuck_saved(chunk, file_system_storage_handler) -> Chunk:
    file_system_storage_handler.write_item(chunk)
    yield chunk


@pytest.fixture
def example_chuck_unsaved(file_system_storage_handler) -> Chunk:
    chunk = Chunk(parent_file_uuid=str(uuid4()), index=1, text="hello", metadata={})
    yield chunk
