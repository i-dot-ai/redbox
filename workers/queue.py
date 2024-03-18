import json
import logging
import time

from abc import abstractmethod

import pika
import pydantic
from pika import spec
from pika.adapters.blocking_connection import BlockingChannel

from redbox.models import (
    EmbeddingResponse,
    EmbedQueueItem,Chunk, Settings,
)

log = logging.getLogger()
log.setLevel(logging.INFO)
env = Settings()


class Queue:
    # Add method for adding message to queue
    # Check that the queue setup wants to process messages before creating a timed processor
    # Coalesce a single method of creating a channel
    channel: BlockingChannel = None

    def __init__(self, queue_uri: str, queue_name: str, max_connection_attempts: int = 10):
        if env.queue == "rabbitmq":
            try:
                connection = env.blocking_connection()
                self.channel = connection.channel()
                self.channel.queue_declare(queue=queue_name, durable=True)
            except Exception:
                raise Exception(f"failed to start with {env.rabbitmq_host}:{env.rabbitmq_port}")
        else:
            logging.info(f"Polling queue {queue_name}")

            connection = None

            for i in range(max_connection_attempts):
                try:
                    logging.debug(f"Attempting to connect to queue {queue_name} (attempt {i}/{max_connection_attempts})")
                    connection = pika.BlockingConnection(
                        parameters=pika.URLParameters(queue_uri),
                    )
                    logging.debug(f"Connected to queue {queue_name}")
                    break
                except Exception as e:
                    logging.error(f"Failed to connect to queue attempt {i}: {e}")
                    time.sleep(5)

            if not connection:
                logging.error("Failed to connect to queue, shutting down")
                return

            self.channel = connection.channel()
            self.channel.queue_declare(queue=queue_name, durable=True)

    def send_message_to_queue(self, chunks: list[Chunk], queue_name: str):
        for chunk in chunks:
            logging.info(f"Writing chunk to storage for chunk uuid: {chunk.uuid}")
            self.channel.basic_publish(
                exchange="redbox-core-exchange",
                routing_key=queue_name,
                body=json.dumps(chunk.model_dump(), ensure_ascii=False),
            )

    def setup_listener(self, queue_name: str, poll_interval: int = 5):
        logging.debug(f"Starting queue poller for {queue_name} every {poll_interval} seconds")
        while True:
            logging.debug(f"Polling queue {queue_name} (every {poll_interval} seconds)")
            self.channel.basic_consume(queue=queue_name, on_message_callback=self.embed_item_callback, auto_ack=False)
            self.channel.start_consuming()
            time.sleep(poll_interval)

    def embed_item_callback(self, channel: BlockingChannel, method: spec.Basic.Deliver, properties: spec.BasicProperties, body: bytes):
        logging.info(f"Received message {method.delivery_tag} by callback")

        try:
            body_dict = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as e:
            logging.error(f"Failed to decode message: {e}")
            channel.basic_nack(delivery_tag=method.delivery_tag)
            return
        try:
            embed_queue_item = EmbedQueueItem(**body_dict)
        except pydantic.ValidationError as e:
            logging.error(f"Failed to validate message: {e}")
            channel.basic_nack(delivery_tag=method.delivery_tag)
            return

        output = self.process_inbound_message()
        output = EmbeddingResponse(**output)

        # TODO: Send the output to Elasticsearch?

        logging.info(f"Embedding ID {output.embedding_id} complete for {method.delivery_tag}")
        channel.basic_ack(delivery_tag=method.delivery_tag)
        channel.stop_consuming()

    @abstractmethod
    def process_inbound_message(self):
        pass
