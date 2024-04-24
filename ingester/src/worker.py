import logging
from datetime import datetime

from fastapi import FastAPI, Depends
from faststream.redis.fastapi import RedisRouter

from sentence_transformers import SentenceTransformer
from redbox.models import EmbedQueueItem, File, Settings, StatusResponse
from redbox.parsing.file_chunker import FileChunker
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


def get_chunker():
    model_db = SentenceTransformer(model_name_or_path=env.embedding_model, cache_folder="/app/models")
    return FileChunker(embedding_model=model_db)


@router.subscriber(channel=env.ingest_queue_name)
async def ingest(
    file: File,
    storage_handler: ElasticsearchStorageHandler = Depends(get_storage_handler),
    chunker: FileChunker = Depends(get_chunker),
):
    """
    1. Chunks file
    2. Puts chunks to ES
    3. Acknowledges message
    4. Puts chunk on embedder-queue
    """

    logging.info(f"Ingesting file: {file}")

    chunks = chunker.chunk_file(file=file)

    logging.info(f"Writing {len(chunks)} chunks to storage for file uuid: {file.uuid}")

    items = storage_handler.write_items(chunks)
    logging.info(f"written {len(items)} chunks to elasticsearch")

    for chunk in chunks:
        queue_item = EmbedQueueItem(chunk_uuid=chunk.uuid)
        logging.info(f"Writing chunk to storage for chunk uuid: {chunk.uuid}")
        await publisher.publish(queue_item)

    return items


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
