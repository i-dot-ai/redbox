import pytest
import hashlib
from redbox.models.file import File


def test_file_creation():
    file = File(
        path="test_path",
        name="test_name",
        type="test_type",
        storage_kind="local",
        creator_user_uuid="test",
    )
    assert file.path == "test_path"
    assert file.name == "test_name"
    assert file.type == "test_type"
    assert file.storage_kind == "local"
    assert file.creator_user_uuid == "test"


def test_model_type():
    file = File(
        path="test_path",
        name="test_name",
        type="test_type",
        storage_kind="local",
        creator_user_uuid="test",
    )
    assert file.model_type == "File"


def test_text_hash():
    file = File(
        path="test_path",
        name="test_name",
        type="test_type",
        storage_kind="local",
        creator_user_uuid="test",
        text="test_text",
    )
    assert file.text_hash == hashlib.md5("test_text".encode()).hexdigest()


def test_token_count():
    file = File(
        path="test_path",
        name="test_name",
        type="test_type",
        storage_kind="local",
        creator_user_uuid="test",
        text="test text",
    )
    assert file.token_count == 2
