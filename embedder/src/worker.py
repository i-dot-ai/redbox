import logging
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


router = RedisRouter(url=env.redis_url)


def get_storage_handler():
    es = env.elasticsearch_client()
    storage_handler = ElasticsearchStorageHandler(es_client=es, root_index="redbox-data")
    model = SentenceTransformer(model_name_or_path=env.embedding_model, cache_folder="/app/models")

    context.set_global("storage_handler", storage_handler)
    context.set_global("model", model)

    yield


@router.subscriber(channel=env.embed_queue_name)
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
