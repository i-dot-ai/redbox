from ingest.src.app import FileIngestor
from redbox.parsing.file_chunker import FileChunker
from redbox.storage import ElasticsearchStorageHandler


def test_ingest_file(s3_client, es_client, embedding_model, file):
    """
    Given that I have written a text File to s3
    When I call ingest_file
    I Expect to see this file to be chunked and written to Elasticsearch
    """

    storage_handler = ElasticsearchStorageHandler(es_client=es_client, root_index="redbox-data")
    chunker = FileChunker(embedding_model=embedding_model)
    file_ingestor = FileIngestor(s3_client, chunker, storage_handler)
    chunks = file_ingestor.ingest_file(file)
    assert chunks
