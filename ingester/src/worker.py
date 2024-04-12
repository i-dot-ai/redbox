import logging
from contextlib import asynccontextmanager

from faststream import Context, ContextRepo, FastStream
from faststream.redis import RedisBroker

from redbox.model_db import SentenceTransformerDB
from redbox.models import EmbedQueueItem, File, Settings
from redbox.parsing.file_chunker import FileChunker
from redbox.storage.elasticsearch import ElasticsearchStorageHandler

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()

env = Settings()


broker = RedisBroker(url=env.redis_url)

publisher = broker.publisher(env.embed_queue_name)


@asynccontextmanager
async def lifespan(context: ContextRepo):
    es = env.elasticsearch_client()
    storage_handler = ElasticsearchStorageHandler(
        es_client=es, root_index="redbox-data"
    )
    model_db = SentenceTransformerDB(env.embedding_model)
    chunker = FileChunker(embedding_model=model_db)

    context.set_global("storage_handler", storage_handler)
    context.set_global("chunker", chunker)

    yield


@broker.subscriber(channel=env.ingest_queue_name)
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


app = FastStream(broker, lifespan=lifespan)
