import pytest

from redbox.model_db import SentenceTransformerDB
from redbox.parsing.file_chunker import FileChunker


@pytest.mark.parametrize("chunk_clustering, expected_chunk_number", [(False, 54), (True, 13)])
def test_chunk_file(file_belonging_to_alice, env, chunk_clustering, expected_chunk_number):
    embedding_model = SentenceTransformerDB(env.embedding_model)
    file_chunker = FileChunker(embedding_model)
    chunks = file_chunker.chunk_file(file_belonging_to_alice, chunk_clustering)
    assert len(chunks) == expected_chunk_number
