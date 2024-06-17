#!/usr/bin/env python

import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from faststream import Context, ContextRepo, FastStream
from faststream.redis import RedisBroker

from redbox.model_db import SentenceTransformerDB
from redbox.models import Chunk, EmbedQueueItem, File, Settings
from redbox.parsing import chunk_file
from redbox.storage.elasticsearch import ElasticsearchStorageHandler

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client
else:
    S3Client = object

start_time = datetime.now(UTC)
logging.basicConfig(level=logging.INFO)
log = logging.getLogger()

env = Settings()


broker = RedisBroker(url=env.redis_url)

publisher = broker.publisher(list=env.embed_queue_name)


@asynccontextmanager
async def lifespan(context: ContextRepo):
    es = env.elasticsearch_client()
    s3_client = env.s3_client()
    storage_handler = ElasticsearchStorageHandler(es_client=es, root_index=env.elastic_root_index)
    model = SentenceTransformerDB(env.embedding_model)

    context.set_global("storage_handler", storage_handler)
    context.set_global("model", model)
    context.set_global("s3_client", s3_client)

    yield


@broker.subscriber(list=env.ingest_queue_name)
async def ingest(
    file: File,
    storage_handler: ElasticsearchStorageHandler = Context(),
    s3_client: S3Client = Context(),
    model: SentenceTransformerDB = Context(),
):
    """
    1. Chunks file
    2. Puts chunks to ES
    3. Acknowledges message
    4. Puts chunk on embedder-queue
    """

    logging.info("Ingesting file: %s", file)

    if env.clustering_strategy == "full":
        logging.info("embedding - full")
        chunks = chunk_file(
            file=file, s3_client=s3_client, embedding_model=model, desired_chunk_size=env.ai.desired_chunk_size
        )
    else:
        logging.info("embedding - None")
        chunks = chunk_file(file=file, s3_client=s3_client, desired_chunk_size=env.ai.desired_chunk_size)

    logging.info("Writing %s chunks to storage for file uuid: %s", len(chunks), file.uuid)

    items = storage_handler.write_items(chunks)
    logging.info("written %s chunks to elasticsearch", len(items))

    for chunk in chunks:
        queue_item = EmbedQueueItem(chunk_uuid=chunk.uuid)
        logging.info("Writing chunk to storage for chunk uuid: %s", chunk.uuid)
        await publisher.publish(queue_item)

    return items


@broker.subscriber(list=env.embed_queue_name)
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
        logging.error("expected just 1 embedding but got %s", len(embedded_sentences.data))
        return
    chunk.embedding = embedded_sentences.data[0].embedding
    storage_handler.update_item(chunk)

    logging.info("embedded: %s", chunk.uuid)


app = FastStream(broker=broker, lifespan=lifespan)
