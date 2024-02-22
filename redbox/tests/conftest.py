from typing import Generator, TypeVar
from uuid import uuid4

import pytest

from models.file import Chunk
from storage.filesystem import FileSystemStorageHandler

T = TypeVar("T")

YieldFixture = Generator[T, None, None]


@pytest.fixture
def file_system_storage_handler(tmp_path) -> YieldFixture[FileSystemStorageHandler]:
    yield FileSystemStorageHandler(tmp_path)


@pytest.fixture
def chunk() -> YieldFixture[Chunk]:
    chunk = Chunk(
        parent_file_uuid="test_uuid",
        index=1,
        text="test_text",
        metadata={},
        creator_user_uuid="test",
    )
    yield chunk


@pytest.fixture
def example_chuck_saved(chunk, file_system_storage_handler) -> YieldFixture[Chunk]:
    file_system_storage_handler.write_item(chunk)
    yield chunk


@pytest.fixture
def example_chuck_unsaved(file_system_storage_handler) -> YieldFixture[Chunk]:
    chunk = Chunk(parent_file_uuid=str(uuid4()), index=1, text="hello", metadata={})
    yield chunk
