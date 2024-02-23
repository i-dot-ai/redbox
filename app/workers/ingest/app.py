import json
import logging
import os

import boto3
import pika
from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer

from redbox.models import File
from redbox.parsing.file_chunker import FileChunker
from redbox.storage.elasticsearch import ElasticsearchStorageHandler

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()

ENV = {
    "ELASTIC_USER": None,
    "ELASTIC_PASSWORD": None,
    "ELASTIC_HOST": None,
    "ELASTIC_PORT": None,
    "ELASTIC_SCHEME": None,
    "OBJECT_STORE": None,
    "EMBEDDING_MODEL": None,  # For chunk clustering
    "BUCKET_NAME": None,
    "INGEST_QUEUE_NAME": None,
    "QUEUE": None,
}

for key in ENV:
    # Throw KeyError if the environment variable is not set
    ENV[key] = os.environ[key]

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

if ENV["OBJECT_STORE"] == "minio":
    for key in ["MINIO_HOST", "MINIO_PORT", "MINIO_ACCESS_KEY", "MINIO_SECRET_KEY"]:
        ENV[key] = os.environ[key]

    s3 = boto3.client(
        "s3",
        aws_access_key_id=ENV["MINIO_ACCESS_KEY"],
        aws_secret_access_key=ENV["MINIO_SECRET_KEY"],
        endpoint_url=f"http://{ENV['MINIO_HOST']}:{ENV['MINIO_PORT']}",
    )
elif ENV["OBJECT_STORE"] == "s3":
    for key in ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION"]:
        ENV[key] = os.environ[key]

    s3 = boto3.client(
        "s3",
        aws_access_key_id=ENV["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=ENV["AWS_SECRET_ACCESS_KEY"],
        region_name=ENV["AWS_REGION"],
    )
else:
    raise ValueError(f"Object store type {ENV['OBJECT_STORE']} not supported")


# === Queues ===

if ENV["QUEUE"] == "rabbitmq":
    for key in ["RABBITMQ_HOST", "RABBITMQ_PORT", "RABBITMQ_USER", "RABBITMQ_PASSWORD"]:
        ENV[key] = os.environ[key]

    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=ENV["RABBITMQ_HOST"],
            port=int(ENV["RABBITMQ_PORT"]),
            credentials=pika.PlainCredentials(
                ENV["RABBITMQ_USER"], ENV["RABBITMQ_PASSWORD"]
            ),
            connection_attempts=5,
            retry_delay=5,
        )
    )
    channel = connection.channel()
    channel.queue_declare(queue=ENV["INGEST_QUEUE_NAME"], durable=True)
elif ENV["QUEUE"] == "sqs":
    for key in ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION"]:
        ENV[key] = os.environ[key]

    sqs = boto3.client(
        "sqs",
        aws_access_key_id=ENV["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=ENV["AWS_SECRET_ACCESS_KEY"],
        region_name=ENV["AWS_REGION"],
    )

    raise NotImplementedError("SQS is not yet implemented")
else:
    raise ValueError(f"Queue type {ENV['QUEUE']} not supported")

# === Storage ===


es = Elasticsearch(
    hosts=[
        {
            "host": ENV["ELASTIC_HOST"],
            "port": int(ENV["ELASTIC_PORT"]),
            "scheme": ENV["ELASTIC_SCHEME"],
        }
    ],
    basic_auth=(ENV["ELASTIC_USER"], ENV["ELASTIC_PASSWORD"]),
)

storage_handler = ElasticsearchStorageHandler(es_client=es, root_index="redbox-data")
chunker = FileChunker(embedding_model=models[ENV["EMBEDDING_MODEL"]])


def ingest_file(file: File):
    logging.info(f"Ingesting file: {file}")

    authenticated_s3_url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": ENV["BUCKET_NAME"], "Key": file.name},
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


channel.basic_consume(queue=ENV["INGEST_QUEUE_NAME"], on_message_callback=callback)
channel.start_consuming()
