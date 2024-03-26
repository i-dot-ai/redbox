import pytest

from redbox.models import Settings
from embedder.src.worker import broker, embed_channel, app
from faststream.rabbit import TestRabbitBroker, TestApp

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

    async with TestRabbitBroker(broker) as br, TestApp(app):
        await br.publish(embed_queue_item, queue=embed_channel)

    embedded_chunk = elasticsearch_storage_handler.read_item(embed_queue_item.chunk_uuid, "Chunk")
    assert embedded_chunk.embedding is not None
