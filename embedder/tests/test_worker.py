import pytest
from faststream.redis import TestApp, TestRedisBroker

from embedder.src.worker import app, broker
from redbox.models import Settings

env = Settings()


@pytest.mark.asyncio
async def test_embed_item_callback(elasticsearch_storage_handler, embed_queue_item):
    """
    Given that I have created and persisted a chunk to ElasticSearch
    When I call embed_queue_item
    I Expect to see that the chunk has been updated with a non null embedding
    """
    unembedded_chunk = elasticsearch_storage_handler.read_item(embed_queue_item.chunk_uuid, "Chunk")
    assert unembedded_chunk.embedding is None

    async with TestRedisBroker(broker) as br, TestApp(app):
        await br.publish(embed_queue_item, channel=env.embed_queue_name)

    embedded_chunk = elasticsearch_storage_handler.read_item(embed_queue_item.chunk_uuid, "Chunk")
    assert embedded_chunk.embedding is not None
