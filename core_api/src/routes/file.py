import logging
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, UploadFile
from fastapi import File as FastAPIFile
from faststream.redis.fastapi import RedisRouter
from pydantic import BaseModel, Field

from core_api.src.auth import get_user_uuid
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

    key: str = Field(description="file key", examples=["policies.pdf"])


@file_app.post("/", tags=["file"])
async def add_file(file_request: FileRequest, user_uuid: Annotated[UUID, Depends(get_user_uuid)]) -> File:
    """Create a File record in the database

    Args:
        file_request (FileRequest): The file to be recorded
        user_uuid (UUID): The UUID of the user

    Returns:
        File: The file uuid from the elastic database
    """

    file = File(key=file_request.key, bucket=env.bucket_name, creator_user_uuid=user_uuid)

    storage_handler.write_item(file)

    log.info("publishing %s for %s", file.uuid, file.creator_user_uuid)
    await file_publisher.publish(file)

    return file


# Standard file upload endpoint for utility in quick testing
if env.dev_mode:

    @file_app.post("/upload", tags=["file"], response_model=File)
    async def upload_file(user_uuid: Annotated[UUID, Depends(get_user_uuid)], file: UploadFile = None) -> File:
        """Upload a file to the object store

        Args:
            file (UploadFile): The file to upload

        Returns:
            File: The file that was uploaded
        """
        file = file or FastAPIFile(...)
        key = file.filename
        s3.upload_fileobj(file.file, env.bucket_name, key)

        file = File(key=key, bucket=env.bucket_name, creator_user_uuid=user_uuid)
        storage_handler.write_item(file)

        log.info("publishing %s", file.uuid)
        await file_publisher.publish(file)

        return file


@file_app.get("/{file_uuid}", response_model=File, tags=["file"])
def get_file(file_uuid: UUID, user_uuid: Annotated[UUID, Depends(get_user_uuid)]) -> File:
    """Get a file from the object store

    Args:
        file_uuid (UUID): The UUID of the file to get
        user_uuid (UUID): The UUID of the user

    Returns:
        File: The file
    """
    file = storage_handler.read_item(file_uuid, model_type="File")
    if file.creator_user_uuid != user_uuid:
        raise HTTPException(status_code=404, detail=f"File {file_uuid} not found")
    return file


@file_app.delete("/{file_uuid}", response_model=File, tags=["file"])
def delete_file(file_uuid: UUID, user_uuid: Annotated[UUID, Depends(get_user_uuid)]) -> File:
    """Delete a file from the object store and the database

    Args:
        file_uuid (UUID): The UUID of the file to delete
        user_uuid (UUID): The UUID of the user

    Returns:
        File: The file that was deleted
    """
    file = storage_handler.read_item(file_uuid, model_type="File")
    if file.creator_user_uuid != user_uuid:
        raise HTTPException(status_code=404)

    s3.delete_object(Bucket=env.bucket_name, Key=file.key)
    storage_handler.delete_item(file)

    chunks = storage_handler.get_file_chunks(file.uuid, user_uuid)
    storage_handler.delete_items(chunks)
    return file


@file_app.get("/{file_uuid}/chunks", tags=["file"])
def get_file_chunks(file_uuid: UUID, user_uuid: Annotated[UUID, Depends(get_user_uuid)]) -> list[Chunk]:
    log.info("getting chunks for file %s", file_uuid)
    return storage_handler.get_file_chunks(file_uuid, user_uuid)


@file_app.get("/{file_uuid}/status", tags=["file"])
def get_file_status(file_uuid: UUID, user_uuid: Annotated[UUID, Depends(get_user_uuid)]) -> FileStatus:
    """Get the status of a file

    Args:
        file_uuid (UUID): The UUID of the file to get the status of
        user_uuid (UUID): The UUID of the user

    Returns:
        File: The file with the updated status
    """
    try:
        status = storage_handler.get_file_status(file_uuid, user_uuid)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=f"File {file_uuid} not found") from e

    return status
