import pytest

from redbox.model_db import SentenceTransformerDB
from redbox.parsing import chunk_file


@pytest.mark.parametrize(("chunk_clustering", "expected_chunk_number"), [(False, 52), (True, 13)])
def test_chunk_file(file_belonging_to_alice, env, chunk_clustering, expected_chunk_number):
    embedding_model = SentenceTransformerDB(env.embedding_model) if chunk_clustering else None
    chunks = chunk_file(
        file_belonging_to_alice,
        s3_client=env.s3_client(),
        embedding_model=embedding_model,
        desired_chunk_size=300,
    )
    assert len(chunks) == expected_chunk_number
