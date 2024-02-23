import json
import logging
import os

from sentence_transformers import SentenceTransformer

from redbox.models import File, Settings
from redbox.parsing.file_chunker import FileChunker
from redbox.storage.elasticsearch import ElasticsearchStorageHandler

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()

env = Settings()

# ====== Loading embedding model ======

available_models = []
models = {}
model_info = {}

# Start of the setup phase
for dirpath, dirnames, filenames in os.walk("models"):
    # Check if the current directory contains a file named "config.json"
    if "pytorch_model.bin" in filenames:
        # If it does, print the path to the directory
        available_models.append(dirpath)

for model_path in available_models:
    model_name = model_path.split("/")[-3]
    model = model_name.split("--")[-1]
    models[model] = SentenceTransformer(model_path)
    logging.info(f"Loaded model {model}")

for model, model_obj in models.items():
    model_info_entry = {
        "model": model,
        "max_seq_length": model_obj.get_max_seq_length(),
        "vector_size": model_obj.get_sentence_embedding_dimension(),
    }

    model_info[model] = model_info_entry


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
