import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from faststream import Context, ContextRepo
from faststream.redis import RedisRouter

from redbox.model_db import SentenceTransformerDB
from redbox.models import EmbedQueueItem, File, Settings, StatusResponse
from redbox.parsing.file_chunker import FileChunker
from redbox.storage.elasticsearch import ElasticsearchStorageHandler

start_time = datetime.now()
logging.basicConfig(level=logging.INFO)
log = logging.getLogger()

env = Settings()


router = RedisRouter(env.redis_url)

publisher = router.publisher(env.embed_queue_name)


@asynccontextmanager
async def lifespan(context: ContextRepo):
    es = env.elasticsearch_client()
    storage_handler = ElasticsearchStorageHandler(es_client=es, root_index="redbox-data")
    model_db = SentenceTransformerDB(env.embedding_model)
    chunker = FileChunker(embedding_model=model_db)

    context.set_global("storage_handler", storage_handler)
    context.set_global("chunker", chunker)

    yield


@router.subscriber(channel=env.ingest_queue_name)
async def ingest(
    file: File,
    storage_handler: ElasticsearchStorageHandler = Context(),
    chunker: FileChunker = Context(),
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
        version="0.1.0",
    )

    return output
