import hashlib

import pytest

from redbox.models.file import Chunk


def test_chunk_creation(chunk):
    assert chunk.parent_file_uuid == "test_uuid"
    assert chunk.index == 1
    assert chunk.text == "test_text"
    assert chunk.metadata == {}


def test_model_type(chunk):
    assert chunk.model_type == "Chunk"


def test_text_hash(chunk):
    assert chunk.text_hash == hashlib.md5("test_text".encode()).hexdigest()


def test_token_count(chunk):
    assert chunk.token_count == 2
