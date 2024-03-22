import json
import logging
from datetime import datetime

import pydantic
from pika.adapters.blocking_connection import BlockingChannel

from redbox.model_db import SentenceTransformerDB
from redbox.models import Chunk, EmbedQueueItem, Settings
from redbox.storage import ElasticsearchStorageHandler

model_db = SentenceTransformerDB()
model_db.init_from_disk()

start_time = datetime.now()
log = logging.getLogger()
log.setLevel(logging.INFO)

env = Settings()

es = env.elasticsearch_client()


def run():
    connection = env.blocking_connection()
    channel = connection.channel()
    channel.queue_declare(queue=env.embed_queue_name, durable=True)
    storage_handler = ElasticsearchStorageHandler(es_client=es, root_index="redbox-data")
    chunk_embedder = ChunkEmbedder(storage_handler)

    channel.basic_consume(
        queue=env.embed_queue_name,
        on_message_callback=chunk_embedder.callback,
        auto_ack=False,
    )
    channel.start_consuming()


class ChunkEmbedder:
    def __init__(self, storage_handler: ElasticsearchStorageHandler):
        self.storage_handler = storage_handler

    def embed_queue_item(self, queue_item: EmbedQueueItem):
        """
        1. embed queue-item text
        2. update related chunk on ES
        """

        chunk: Chunk = self.storage_handler.read_item(queue_item.chunk_uuid, "Chunk")
        embedded_sentences = model_db.embed_sentences(queue_item.model, [chunk.text])
        if len(embedded_sentences.data) != 1:
            logging.error(f"expected just 1 embedding but got {len(embedded_sentences.data)}")
            return
        chunk.embedding = embedded_sentences.data[0].embedding
        self.storage_handler.update_item(chunk.uuid, chunk)

    def callback(self, ch: BlockingChannel, method, properties, body):
        logging.info(f"Received message {method.delivery_tag} by callback")
        try:
            body_dict = json.loads(body.decode("utf-8"))
            embed_queue_item = EmbedQueueItem(**body_dict)
            self.embed_queue_item(embed_queue_item)
            logging.info(f"Embedded message: {method.delivery_tag}")
        except json.JSONDecodeError as e:
            logging.error(f"Failed to decode message: {e}")
        except pydantic.ValidationError as e:
            logging.error(f"Failed to validate message: {e}")
        finally:
            ch.basic_ack(delivery_tag=method.delivery_tag)


if __name__ == "__main__":
    run()
