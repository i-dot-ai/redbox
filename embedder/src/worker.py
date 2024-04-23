import logging
from contextlib import asynccontextmanager
from datetime import datetime

from faststream import Context, ContextRepo, FastStream
from faststream.redis import RedisBroker
from sentence_transformers import SentenceTransformer

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
    model = SentenceTransformer(model_name_or_path=env.embedding_model, cache_folder="/app/models")

    context.set_global("storage_handler", storage_handler)
    context.set_global("model", model)

    yield


@broker.subscriber(channel=env.embed_queue_name)
async def embed(
    queue_item: EmbedQueueItem,
    storage_handler: ElasticsearchStorageHandler = Context(),
    model: SentenceTransformer = Context(),
):
    """
    1. embed queue-item text
    2. update related chunk on ES
    """

    chunk: Chunk = storage_handler.read_item(queue_item.chunk_uuid, "Chunk")
    embedded_sentences = model.encode([chunk.text]).tolist()
    chunk.embedding = embedded_sentences[0]
    storage_handler.update_item(chunk)


app = FastStream(broker, lifespan=lifespan)
