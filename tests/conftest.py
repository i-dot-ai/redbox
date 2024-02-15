from uuid import uuid4

import pytest

from redbox.models import Chunk
from redbox.storage import FileSystemStorageHandler


@pytest.fixture
def uuid_str() -> str:
    yield str(uuid4())


@pytest.fixture
def example_chuck(uuid_str) -> Chunk:
    yield Chunk(parent_file_uuid=uuid_str, index=1, text="hello", metadata={})




@pytest.fixture
def file_system_storage_handler(tmp_path) -> FileSystemStorageHandler:
    yield FileSystemStorageHandler(tmp_path)


@pytest.fixture
def saved_example_chuck(example_chuck, file_system_storage_handler) -> Chunk:
    file_system_storage_handler.write_item(example_chuck)
    yield example_chuck
