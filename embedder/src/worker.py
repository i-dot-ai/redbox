import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from faststream import Context, ContextRepo
from faststream.redis import RedisRouter

from redbox.model_db import SentenceTransformerDB
from redbox.models import Chunk, EmbedQueueItem, Settings, StatusResponse
from redbox.storage import ElasticsearchStorageHandler

start_time = datetime.now()
log = logging.getLogger()
log.setLevel(logging.INFO)

env = Settings()

router = RedisRouter(env.redis_url)


@asynccontextmanager
async def lifespan(context: ContextRepo):
    es = env.elasticsearch_client()
    storage_handler = ElasticsearchStorageHandler(es_client=es, root_index="redbox-data")
    model = SentenceTransformerDB(env.embedding_model)

    context.set_global("storage_handler", storage_handler)
    context.set_global("model", model)

    yield


@router.subscriber(channel=env.embed_queue_name)
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


app = FastAPI(lifespan=router.lifespan_context)
app.include_router(router)


@app.get("/health", tags=["health"])
def health() -> StatusResponse:
    """Returns the health of the API

    Returns:
        StatusResponse: The health of the API
    """

    uptime = datetime.now() - start_time
    uptime_seconds = uptime.total_seconds()

    output = StatusResponse(
        status="ready",
        uptime_seconds=uptime_seconds,
        version="0.1.0",
    )

    return output
