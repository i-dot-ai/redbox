import pytest
from faststream.redis import TestApp, TestRedisBroker

from redbox.storage import ElasticsearchStorageHandler
from worker.src.app import app, broker, env


@pytest.mark.asyncio()
async def test_ingest_file(es_client, file):
    """
    Given that I have written a text File to s3
    When I call ingest_file
    I Expect to see this file to be:
    1. chunked
    2. written to Elasticsearch
    """

    storage_handler = ElasticsearchStorageHandler(es_client=es_client, root_index=env.elastic_root_index)

    storage_handler.write_item(file)

    async with TestRedisBroker(broker) as br, TestApp(app):
        await br.publish(file, list=env.ingest_queue_name)

        file = storage_handler.read_item(
            item_uuid=file.uuid,
            model_type="File",
        )

        assert file is not None


@pytest.mark.asyncio()
async def test_embed_item_callback(elasticsearch_storage_handler, embed_queue_item):
    """
    Given that I have created and persisted a chunk to ElasticSearch
    When I call embed_queue_item
    I Expect to see that the chunk has been updated with a non null embedding
    """
    unembedded_chunk = elasticsearch_storage_handler.read_item(embed_queue_item.chunk_uuid, "Chunk")
    assert unembedded_chunk.embedding is None

    async with TestRedisBroker(broker) as br:
        await br.publish(embed_queue_item, list=env.embed_queue_name)

    embedded_chunk = elasticsearch_storage_handler.read_item(embed_queue_item.chunk_uuid, "Chunk")
    assert embedded_chunk.embedding is not None
