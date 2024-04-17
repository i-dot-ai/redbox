import logging
from uuid import UUID

from fastapi import FastAPI, HTTPException
from faststream.redis.fastapi import RedisRouter
from pydantic import BaseModel, Field

from core_api.src.publisher_handler import FilePublisher
from redbox.models import Chunk, File, FileStatus, Settings
from redbox.storage import ElasticsearchStorageHandler

# === Logging ===

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()

env = Settings()


# === Object Store ===

s3 = env.s3_client()


# === Queues ===
router = RedisRouter(url=env.redis_url)

file_publisher = FilePublisher(router.broker, env.ingest_queue_name)

# === Storage ===

es = env.elasticsearch_client()
storage_handler = ElasticsearchStorageHandler(es_client=es, root_index="redbox-data")


file_app = FastAPI(
    title="Core File API",
    description="Redbox Core File API",
    version="0.1.0",
    openapi_tags=[
        {"name": "file", "description": "File endpoints"},
    ],
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=router.lifespan_context,
)
file_app.include_router(router)


class FileRequest(BaseModel):
    """Reference to file stored on s3"""

    key: str = Field(description="file key", examples=["sales.csv", "README.txt"])
    bucket: str = Field(description="s3 bucket", examples=[env.bucket_name])


@file_app.post("/", tags=["file"])
async def add_file(file_request: FileRequest) -> File:
    """Create a File record in the database

    Args:
        file_request (FileRequest): The file to be recorded

    Returns:
        File: The file uuid from the elastic database
    """

    file = File(key=file_request.key, bucket=file_request.bucket)

    storage_handler.write_item(file)

    log.info(f"publishing {file.uuid}")
    await file_publisher.publish(file)

    return file


@file_app.get("/{file_uuid}", response_model=File, tags=["file"])
def get_file(file_uuid: UUID) -> File:
    """Get a file from the object store

    Args:
        file_uuid (str): The UUID of the file to get

    Returns:
        File: The file
    """
    return storage_handler.read_item(file_uuid, model_type="File")


@file_app.delete("/{file_uuid}", response_model=File, tags=["file"])
def delete_file(file_uuid: UUID) -> File:
    """Delete a file from the object store and the database

    Args:
        file_uuid (str): The UUID of the file to delete

    Returns:
        File: The file that was deleted
    """
    file = storage_handler.read_item(file_uuid, model_type="File")
    s3.delete_object(Bucket=env.bucket_name, Key=file.key)
    storage_handler.delete_item(file)

    chunks = storage_handler.get_file_chunks(file.uuid)
    storage_handler.delete_items(chunks)
    return file


@file_app.get("/{file_uuid}/chunks", tags=["file"])
def get_file_chunks(file_uuid: UUID) -> list[Chunk]:
    log.info(f"getting chunks for file {file_uuid}")
    return storage_handler.get_file_chunks(file_uuid)


@file_app.get("/{file_uuid}/status", tags=["file"])
def get_file_status(file_uuid: UUID) -> FileStatus:
    """Get the status of a file

    Args:
        file_uuid (str): The UUID of the file to get the status of

    Returns:
        File: The file with the updated status
    """
    try:
        status = storage_handler.get_file_status(file_uuid)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"File {file_uuid} not found")

    return status
