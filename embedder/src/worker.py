import logging
from contextlib import asynccontextmanager
from datetime import datetime

from faststream import Context, ContextRepo, FastStream
from faststream.redis import RedisBroker

from redbox.model_db import SentenceTransformerDB
from redbox.models import Chunk, EmbedQueueItem, Settings
from redbox.storage import ElasticsearchStorageHandler

start_time = datetime.now()
log = logging.getLogger()
log.setLevel(logging.INFO)

env = Settings()


broker = RedisBroker(url=env.redis_url)


@asynccontextmanager
async def lifespan(context: ContextRepo):
    es = env.elasticsearch_client()
    storage_handler = ElasticsearchStorageHandler(es_client=es, root_index="redbox-data")
    model = SentenceTransformerDB(env.embedding_model)

    context.set_global("storage_handler", storage_handler)
    context.set_global("model", model)

    yield


@broker.subscriber(channel=env.embed_queue_name)
async def embed(
    queue_item: EmbedQueueItem,
    storage_handler: ElasticsearchStorageHandler = Context(),
    model: SentenceTransformerDB = Context(),
):
    """
    1. embed queue-item text
    2. update related chunk on ES
    """

    chunk: Chunk = storage_handler.read_item(queue_item.chunk_uuid, "Chunk")
    embedded_sentences = model.embed_sentences([chunk.text])
    if len(embedded_sentences.data) != 1:
        logging.error(f"expected just 1 embedding but got {len(embedded_sentences.data)}")
        return
    chunk.embedding = embedded_sentences.data[0].embedding
    storage_handler.update_item(chunk)


app = FastStream(broker, lifespan=lifespan)
