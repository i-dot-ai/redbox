import pytest

from redbox.model_db import SentenceTransformerDB
from redbox.models import Settings
from redbox.parsing.file_chunker import FileChunker

env = Settings()


@pytest.mark.parametrize("chunk_clustering, expected_chunk_number", [(False, 54), (True, 13)])
def test_chunk_file(file, chunk_clustering, expected_chunk_number):
    embedding_model = SentenceTransformerDB(model_name=env.embedding_model)
    file_chunker = FileChunker(embedding_model)
    chunks = file_chunker.chunk_file(file, chunk_clustering)
    assert len(chunks) == expected_chunk_number
