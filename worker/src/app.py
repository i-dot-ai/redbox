#!/usr/bin/env python

import logging
from contextlib import asynccontextmanager
from datetime import datetime

from faststream import Context, ContextRepo, FastStream
from faststream.redis import RedisBroker

from redbox.model_db import SentenceTransformerDB
from redbox.models import Chunk, EmbedQueueItem, File, Settings
from redbox.parsing import chunk_file
from redbox.storage.elasticsearch import ElasticsearchStorageHandler

start_time = datetime.now()
logging.basicConfig(level=logging.INFO)
log = logging.getLogger()

env = Settings()


broker = RedisBroker(url=env.redis_url)

publisher = broker.publisher(list=env.embed_queue_name)


@asynccontextmanager
async def lifespan(context: ContextRepo):
    es = env.elasticsearch_client()
    storage_handler = ElasticsearchStorageHandler(es_client=es, root_index="redbox-data")
    model = SentenceTransformerDB(env.embedding_model)

    context.set_global("storage_handler", storage_handler)
    context.set_global("model", model)

    yield


@broker.subscriber(list=env.ingest_queue_name)
async def ingest(
    file: File,
    storage_handler: ElasticsearchStorageHandler = Context(),
):
    """
    1. Chunks file
    2. Puts chunks to ES
    3. Acknowledges message
    4. Puts chunk on embedder-queue
    """

    logging.info("Ingesting file: %s", file)

    chunks = chunk_file(file=file)  # , embedding_model=embedding_model)

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
