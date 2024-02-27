import json
import logging
from datetime import datetime
from uuid import UUID

import pika
import pydantic
from fastapi import FastAPI, UploadFile
from fastapi.responses import RedirectResponse

from redbox.models import File, Settings
from redbox.storage.elasticsearch import ElasticsearchStorageHandler

# === Logging ===

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()

env = Settings()


# === Object Store ===

s3 = env.minio_client()


# === Queues ===

if env.queue == "rabbitmq":
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=env.rabbitmq_host,
            port=env.rabbitmq_port,
            credentials=pika.PlainCredentials(env.rabbitmq_user, env.rabbitmq_password),
            connection_attempts=5,
            retry_delay=5,
        )
    )
    channel = connection.channel()
    channel.queue_declare(queue=env.ingest_queue_name, durable=True)

elif env.queue == "sqs":
    sqs = env.sqs_client()
    raise NotImplementedError("SQS is not yet implemented")


# === Storage ===

es = env.elasticsearch_client()


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
        Bucket=env.bucket_name,
        Body=file.file,
        Key=file.filename,
        Tagging=f"file_type={file.content_type}",
    )

    authenticated_s3_url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": env.bucket_name, "Key": file.filename},
        ExpiresIn=3600,
    )
    # Strip off the query string (we don't need the keys)
    simple_s3_url = authenticated_s3_url.split("?")[0]
    if file.filename is None:
        raise ValueError("file name is null")
    if file.content_type is None:
        raise ValueError("file type is null")
    file_record = File(
        name=file.filename,
        path=simple_s3_url,
        type=file.content_type,
        creator_user_uuid="dev",
        storage_kind=env.object_store,
    )

    storage_handler.write_item(file_record)

    if ingest:
        ingest_file(file_record.uuid)

    return file_record


@app.get("/file/{file_uuid}", response_model=File, tags=["file"])
def get_file(file_uuid: UUID) -> File:
    """Get a file from the object store

    Args:
        file_uuid (str): The UUID of the file to get

    Returns:
        File: The file
    """
    return storage_handler.read_item(str(file_uuid), model_type="File")


@app.post("/file/{file_uuid}/delete", response_model=File, tags=["file"])
def delete_file(file_uuid: str) -> File:
    """Delete a file from the object store and the database

    Args:
        file_uuid (str): The UUID of the file to delete

    Returns:
        File: The file that was deleted
    """
    file = storage_handler.read_item(file_uuid, model_type="File")
    s3.delete_object(Bucket=env.bucket_name, Key=file.name)
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
        routing_key=env.ingest_queue_name,
        body=json.dumps(file.model_dump(), ensure_ascii=False),
    )

    return file
