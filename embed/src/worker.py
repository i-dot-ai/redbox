import logging
from datetime import datetime

from fast_depends import Depends
from faststream import FastStream
from faststream.rabbit import RabbitBroker, RabbitQueue

from redbox.model_db import SentenceTransformerDB
from redbox.models import Chunk, EmbedQueueItem, Settings
from redbox.storage import ElasticsearchStorageHandler


start_time = datetime.now()
log = logging.getLogger()
log.setLevel(logging.INFO)

env = Settings()


broker = RabbitBroker(f"amqp://{env.rabbitmq_user}:{env.rabbitmq_password}@{env.rabbitmq_host}:{env.rabbitmq_port}/")
app = FastStream(broker)

embed_channel = RabbitQueue(name=env.embed_queue_name, durable=True)


def get_storage() -> ElasticsearchStorageHandler:
    es = env.elasticsearch_client()
    storage_handler = ElasticsearchStorageHandler(es_client=es, root_index="redbox-data")
    return storage_handler


def get_model_db() -> SentenceTransformerDB:
    model_db = SentenceTransformerDB()
    return model_db


@broker.subscriber(queue=embed_channel)
async def embed(
    queue_item: EmbedQueueItem,
    elasticsearch_storage_handler: ElasticsearchStorageHandler = Depends(get_storage),
    model_db: SentenceTransformerDB = Depends(get_model_db),
):
    """
    1. embed queue-item text
    2. update related chunk on ES
    """

    chunk: Chunk = elasticsearch_storage_handler.read_item(queue_item.chunk_uuid, "Chunk")
    embedded_sentences = model_db.embed_sentences(queue_item.model, [chunk.text])
    if len(embedded_sentences.data) != 1:
        logging.error(f"expected just 1 embedding but got {len(embedded_sentences.data)}")
        return
    chunk.embedding = embedded_sentences.data[0].embedding
    elasticsearch_storage_handler.update_item(chunk.uuid, chunk)
