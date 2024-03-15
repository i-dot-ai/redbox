import json

from ingest.src.app import FileIngestor
from redbox.models import Settings
from redbox.models import ProcessingStatusEnum
from redbox.parsing.file_chunker import FileChunker
from redbox.storage import ElasticsearchStorageHandler

env = Settings()


def test_ingest_file(s3_client, es_client, embedding_model, file, rabbitmq_channel):
    """
    Given that I have written a text File to s3
    When I call ingest_file
    I Expect to see this file to be:
    1. chunked
    2. written to Elasticsearch
    3. a message put on the embed-queue
    """

    storage_handler = ElasticsearchStorageHandler(es_client=es_client, root_index="redbox-data")
    chunker = FileChunker(embedding_model=embedding_model)
    file_ingestor = FileIngestor(s3_client, chunker, storage_handler, rabbitmq_channel)
    chunks = file_ingestor.ingest_file(file)
    assert chunks
    assert (
        storage_handler.read_item(
            item_uuid=file.uuid,
            model_type="file",
        ).processing_status
        is ProcessingStatusEnum.chunking
    )

    _method, _properties, body = rabbitmq_channel.basic_get(env.embed_queue_name)
    msg = json.loads(body)
    assert msg["model"] == env.embedding_model
