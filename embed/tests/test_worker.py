from redbox.models import Settings
from embed.src.worker import embed, get_model_db

env = Settings()


def test_embed_item_callback(elasticsearch_storage_handler, embed_queue_item):
    """
    Given that I have created and persisted a chunk to ElasticSearch
    When I call embed_queue_item
    I Expect to see that the chunk has been updated with a non null embedding
    """
    unembedded_chunk = elasticsearch_storage_handler.read_item(embed_queue_item.chunk_uuid, "Chunk")
    assert unembedded_chunk.embedding is None

    # chunk_embedder = ChunkEmbedder(elasticsearch_storage_handler)
    # chunk_embedder.embed_queue_item(embed_queue_item)
    embed(embed_queue_item, elasticsearch_storage_handler, get_model_db())

    embedded_chunk = elasticsearch_storage_handler.read_item(embed_queue_item.chunk_uuid, "Chunk")
    assert embedded_chunk.embedding is not None
