import pathlib

import pytest

from redbox.models.file import File
from redbox.parsing.file_chunker import FileChunker


def test_file_chunker():
    target_file_path = pathlib.Path("tests/data/pdf/Cabinet Office - Wikipedia.pdf")

    file = File(
        path=str(target_file_path),
        name=target_file_path.name,
        type=target_file_path.suffix,
        storage_kind="local",
        creator_user_uuid="test",
    )

    chunker = FileChunker()

    chunks = chunker.chunk_file(file)

    assert len(chunks) > 0
