import json
import logging
import os
from datetime import datetime

import boto3
import pika
import pydantic
from elasticsearch import Elasticsearch
from fastapi import FastAPI, UploadFile
from fastapi.responses import RedirectResponse

from redbox.models import File
from redbox.storage.elasticsearch import ElasticsearchStorageHandler

# === Logging ===

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()

ENV = {
    "ELASTIC_USER": None,
    "ELASTIC_PASSWORD": None,
    "ELASTIC_HOST": None,
    "ELASTIC_PORT": None,
    "ELASTIC_SCHEME": None,
    "OBJECT_STORE": None,
    "BUCKET_NAME": None,
    "INGEST_QUEUE_NAME": None,
    "QUEUE": None,
}

for key in ENV:
    # Throw KeyError if the environment variable is not set
    ENV[key] = os.environ[key]

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

# === Data Models ===


class StatusResponse(pydantic.BaseModel):
    status: str
    uptime_seconds: float
    version: str


# === API Setup ===

start_time = datetime.now()
IS_READY = True


# Create API

app = FastAPI(
    title="Core API",
    description="Redbox Core API",
    version="0.1.0",
    openapi_tags=[
        {"name": "health", "description": "Health check"},
    ],
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# === API Routes ===

# Basic Setup


@app.get("/", include_in_schema=False, response_class=RedirectResponse)
def root():
    return RedirectResponse(url="/docs")


@app.get("/health", response_model=StatusResponse, tags=["health"])
def health():
    """Returns the health of the API

    Returns:
        StatusResponse: The health of the API
    """

    uptime = datetime.now() - start_time
    uptime_seconds = uptime.total_seconds()

    output = {"status": None, "uptime_seconds": uptime_seconds, "version": app.version}

    if IS_READY:
        output["status"] = "ready"
    else:
        output["status"] = "loading"

    return output


@app.post("/file/upload", response_model=File, tags=["file"])
async def create_upload_file(file: UploadFile, ingest=True) -> File:
    """Upload a file to the object store and create a record in the database

    Args:
        file (UploadFile): The file to upload

    Returns:
        File: The file record
    """

    s3.put_object(
        Bucket=ENV["BUCKET_NAME"],
        Body=file.file,
        Key=file.filename,
        Tagging=f"file_type={file.content_type}",
    )

    authenticated_s3_url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": ENV["BUCKET_NAME"], "Key": file.filename},
        ExpiresIn=3600,
    )
    # Strip off the query string (we don't need the keys)
    simple_s3_url = authenticated_s3_url.split("?")[0]

    file_record = File(
        name=file.filename,
        path=simple_s3_url,
        type=file.content_type,
        creator_user_uuid="dev",
        storage_kind=ENV["OBJECT_STORE"],
    )

    storage_handler.write_item(file_record)

    if ingest:
        ingest_file(file_record.uuid)

    return file_record


@app.get("/file/{file_uuid}", response_model=File, tags=["file"])
def get_file(file_uuid: str) -> File:
    """Get a file from the object store

    Args:
        file_uuid (str): The UUID of the file to get

    Returns:
        File: The file
    """
    return storage_handler.read_item(file_uuid, model_type="File")


@app.post("/file/{file_uuid}/delete", response_model=File, tags=["file"])
def delete_file(file_uuid: str) -> File:
    """Delete a file from the object store and the database

    Args:
        file_uuid (str): The UUID of the file to delete

    Returns:
        File: The file that was deleted
    """
    file = storage_handler.read_item(file_uuid, model_type="File")
    s3.delete_object(Bucket=ENV["BUCKET_NAME"], Key=file.name)
    storage_handler.delete_item(file_uuid, model_type="File")
    return file


@app.post("/file/ingest/{file_uuid}", response_model=File, tags=["file"])
def ingest_file(file_uuid: str) -> File:
    """Trigger the ingest process for a file to a queue.

    Args:
        file_uuid (str): The UUID of the file to ingest

    Returns:
        File: The file that was ingested
    """
    file = storage_handler.read_item(file_uuid, model_type="File")

    channel.basic_publish(
        exchange="redbox-core-exchange",
        routing_key=ENV["INGEST_QUEUE_NAME"],
        body=json.dumps(file.model_dump(), ensure_ascii=False),
    )

    return file
