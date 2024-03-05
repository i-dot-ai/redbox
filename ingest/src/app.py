import json
import logging

from model_db import SentenceTransformerDB
from redbox.models import File, Settings
from redbox.parsing.file_chunker import FileChunker
from redbox.storage.elasticsearch import ElasticsearchStorageHandler

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()

env = Settings()

# ====== Loading embedding model ======

models = SentenceTransformerDB()

models.init_from_disk()


# === Object Store ===

s3 = env.s3_client()


# === Queues ===

if env.queue == "rabbitmq":
    connection = env.blocking_connection()
    channel = connection.channel()
    channel.queue_declare(queue=env.ingest_queue_name, durable=True)
elif env.queue == "sqs":
    sqs = env.sqs_client()
    raise NotImplementedError("SQS is not yet implemented")
else:
    raise ValueError("must use rabbitmq")

# === Storage ===


es = env.elasticsearch_client()

storage_handler = ElasticsearchStorageHandler(es_client=es, root_index="redbox-data")
chunker = FileChunker(embedding_model=models[env.embedding_model])


def ingest_file(file: File):
    logging.info(f"Ingesting file: {file}")

    authenticated_s3_url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": env.bucket_name, "Key": file.name},
        ExpiresIn=180,
    )

    chunks = chunker.chunk_file(
        file=file,
        file_url=authenticated_s3_url,
        creator_user_uuid=file.creator_user_uuid,
    )

    logging.info(f"Writing {len(chunks)} chunks to storage for file uuid: {file.uuid}")

    storage_handler.write_items(chunks)


def callback(ch, method, properties, body):
    logging.info("Received message")
    file = File(**json.loads(body))
    logging.info(f"Starting ingest for file (uuid: {file.uuid}, name: {file.name})")
    ingest_file(file)
    ch.basic_ack(delivery_tag=method.delivery_tag)


channel.basic_consume(queue=env.ingest_queue_name, on_message_callback=callback)
channel.start_consuming()
