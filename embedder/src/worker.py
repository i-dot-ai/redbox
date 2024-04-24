import logging
from datetime import datetime

from fastapi import FastAPI, Depends
from faststream.redis.fastapi import RedisRouter
from sentence_transformers import SentenceTransformer

from redbox.models import Chunk, EmbedQueueItem, Settings, StatusResponse
from redbox.storage import ElasticsearchStorageHandler

start_time = datetime.now()
log = logging.getLogger()
log.setLevel(logging.INFO)

env = Settings()


router = RedisRouter(url=env.redis_url)


def get_storage_handler():
    es = env.elasticsearch_client()
    return ElasticsearchStorageHandler(es_client=es, root_index="redbox-data")


def get_model():
    model = SentenceTransformer(model_name_or_path=env.embedding_model, cache_folder="/app/models")
    return model


@router.subscriber(channel=env.embed_queue_name)
async def embed(
    queue_item: EmbedQueueItem,
    storage_handler: ElasticsearchStorageHandler = Depends(get_storage_handler),
    model: SentenceTransformer = Depends(get_model),
):
    """
    1. embed queue-item text
    2. update related chunk on ES
    """

    chunk: Chunk = storage_handler.read_item(queue_item.chunk_uuid, "Chunk")
    embedded_sentences = model.embed_documents([chunk.text])
    if len(embedded_sentences.data) != 1:
        logging.error(f"expected just 1 embedding but got {len(embedded_sentences.data)}")
        return
    chunk.embedding = embedded_sentences[0]
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
        version=app.version,
    )

    return output
