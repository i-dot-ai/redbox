import logging
from contextlib import asynccontextmanager

from faststream import FastStream, ContextRepo, Context
from faststream.rabbit import RabbitBroker, RabbitQueue, RabbitExchange

from redbox.model_db import SentenceTransformerDB
from redbox.models import EmbedQueueItem, File, ProcessingStatusEnum, Settings
from redbox.parsing.file_chunker import FileChunker
from redbox.storage.elasticsearch import ElasticsearchStorageHandler

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()

env = Settings()


broker = RabbitBroker(env.rabbit_url)

ingest_channel = RabbitQueue(name=env.ingest_queue_name, durable=True)

embed_channel = RabbitQueue(name=env.embed_queue_name, durable=True)

publisher = broker.publisher(
    embed_channel,
    exchange=RabbitExchange("redbox-core-exchange", durable=True),
)


@asynccontextmanager
async def lifespan(context: ContextRepo):
    s3_client = env.s3_client()
    es = env.elasticsearch_client()
    storage_handler = ElasticsearchStorageHandler(es_client=es, root_index="redbox-data")
    model_db = SentenceTransformerDB(env.embedding_model)
    chunker = FileChunker(embedding_model=model_db)

    context.set_global("s3_client", s3_client)
    context.set_global("storage_handler", storage_handler)
    context.set_global("chunker", chunker)

    yield


@broker.subscriber(queue=ingest_channel)
async def ingest(
    file: File,
    s3_client=Context(),
    storage_handler: ElasticsearchStorageHandler = Context(),
    chunker: FileChunker = Context(),
):
    """
    1. Chunks file
    2. Puts chunks to ES
    3. Acknowledges message
    4. Puts chunk on embed-queue
    """

    logging.info(f"Ingesting file: {file}")

    authenticated_s3_url = s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": env.bucket_name, "Key": file.name},
        ExpiresIn=180,
    )

    file.processing_status = ProcessingStatusEnum.chunking
    storage_handler.update_item(file.uuid, file)

    chunks = chunker.chunk_file(
        file=file,
        file_url=authenticated_s3_url,
        creator_user_uuid=file.creator_user_uuid,
    )

    logging.info(f"Writing {len(chunks)} chunks to storage for file uuid: {file.uuid}")

    items = storage_handler.write_items(chunks)
    logging.info(f"written {len(items)} chunks to elasticsearch")

    for chunk in chunks:
        queue_item = EmbedQueueItem(chunk_uuid=chunk.uuid)
        logging.info(f"Writing chunk to storage for chunk uuid: {chunk.uuid}")
        await publisher.publish(queue_item)
    return items


app = FastStream(broker, lifespan=lifespan)
