import pytest
import hashlib
from redbox.models.file import Chunk


def test_chunk_creation():
    chunk = Chunk(
        parent_file_uuid="test_uuid",
        index=1,
        text="test_text",
        metadata={},
        creator_user_uuid="test",
    )
    assert chunk.parent_file_uuid == "test_uuid"
    assert chunk.index == 1
    assert chunk.text == "test_text"
    assert chunk.metadata == {}


def test_model_type():
    chunk = Chunk(
        parent_file_uuid="test_uuid",
        index=1,
        text="test_text",
        metadata={},
        creator_user_uuid="test",
    )
    assert chunk.model_type == "Chunk"


def test_text_hash():
    chunk = Chunk(
        parent_file_uuid="test_uuid",
        index=1,
        text="test_text",
        metadata={},
        creator_user_uuid="test",
    )
    assert chunk.text_hash == hashlib.md5("test_text".encode()).hexdigest()


def test_token_count():
    chunk = Chunk(
        parent_file_uuid="test_uuid",
        index=1,
        text="test text",
        metadata={},
        creator_user_uuid="test",
    )
    assert chunk.token_count == 2
