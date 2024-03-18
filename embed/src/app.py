import json
import logging

import pydantic
from pika.adapters.blocking_connection import BlockingChannel

from core_api.src.app import embed_sentences
from redbox.models import (
    EmbedQueueItem,
    Settings,
)

log = logging.getLogger()
log.setLevel(logging.INFO)


env = Settings()


def run():
    connection = env.blocking_connection()
    channel = connection.channel()
    channel.queue_declare(queue=env.embed_queue_name, durable=True)
    channel.basic_consume(queue=env.embed_queue_name, on_message_callback=embed_item_callback, auto_ack=False)
    channel.start_consuming()


def embed_item_callback(ch: BlockingChannel, method, properties, body):
    logging.info(f"Received message {method.delivery_tag} by callback")
    try:
        body_dict = json.loads(body.decode("utf-8"))
        embed_queue_item = EmbedQueueItem(**body_dict)
        response = embed_sentences(embed_queue_item.model, [embed_queue_item.sentence])
        logging.info(f"Embedding ID {response['embedding_id']} complete for {method.delivery_tag}")
    except json.JSONDecodeError as e:
        logging.error(f"Failed to decode message: {e}")
    except pydantic.ValidationError as e:
        logging.error(f"Failed to validate message: {e}")
    finally:
        ch.basic_ack(delivery_tag=method.delivery_tag)


if __name__ == "__main__":
    run()
