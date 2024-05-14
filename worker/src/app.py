import logging
from datetime import datetime

from fastapi import Depends, FastAPI
from faststream.redis.fastapi import RedisRouter

from redbox.model_db import SentenceTransformerDB
from redbox.models import Chunk, EmbedQueueItem, File, Settings, StatusResponse
from redbox.parsing import chunk_file
from redbox.storage.elasticsearch import ElasticsearchStorageHandler

start_time = datetime.now()
logging.basicConfig(level=logging.INFO)
log = logging.getLogger()

env = Settings()


router = RedisRouter(url=env.redis_url)

publisher = router.broker.publisher(env.embed_queue_name)


def get_storage_handler():
    es = env.elasticsearch_client()
    return ElasticsearchStorageHandler(es_client=es, root_index="redbox-data")


def get_model() -> SentenceTransformerDB:
    model = SentenceTransformerDB(env.embedding_model)
    return model


@router.subscriber(channel=env.ingest_queue_name)
async def ingest(
    file: File,
    storage_handler: ElasticsearchStorageHandler = Depends(get_storage_handler),
    embedding_model: SentenceTransformerDB = Depends(get_model),
):
    """
    1. Chunks file
    2. Puts chunks to ES
    3. Acknowledges message
    4. Puts chunk on embedder-queue
    """

    logging.info("Ingesting file: %s", file)

    chunks = chunk_file(file=file, embedding_model=embedding_model)

    logging.info("Writing %s chunks to storage for file uuid: %s", len(chunks), file.uuid)

    items = storage_handler.write_items(chunks)
    logging.info("written %s chunks to elasticsearch", len(items))

    for chunk in chunks:
        queue_item = EmbedQueueItem(chunk_uuid=chunk.uuid)
        logging.info("Writing chunk to storage for chunk uuid: %s", chunk.uuid)
        await publisher.publish(queue_item)

    return items


@router.subscriber(channel=env.embed_queue_name)
async def embed(
    queue_item: EmbedQueueItem,
    storage_handler: ElasticsearchStorageHandler = Depends(get_storage_handler),
    embedding_model: SentenceTransformerDB = Depends(get_model),
):
    """
    1. embed queue-item text
    2. update related chunk on ES
    """

    chunk: Chunk = storage_handler.read_item(queue_item.chunk_uuid, "Chunk")
    embedded_sentences = embedding_model.embed_sentences([chunk.text])
    if len(embedded_sentences.data) != 1:
        logging.error("expected just 1 embedding but got %s", len(embedded_sentences.data))
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
        version=app.version,
    )

    return output
