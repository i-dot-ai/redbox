import logging
from typing import Annotated
from uuid import UUID

from elasticsearch import NotFoundError
from fastapi import Depends, FastAPI, UploadFile
from fastapi import File as FastAPIFile
from fastapi.responses import JSONResponse
from faststream.redis.fastapi import RedisRouter
from pydantic import BaseModel, Field

from core_api.src.auth import get_user_uuid
from core_api.src.publisher_handler import FilePublisher
from redbox.models import APIError404, Chunk, File, FileStatus, Settings
from redbox.storage import ElasticsearchStorageHandler

# === Functions ===


def file_not_found_response(file_uuid: UUID) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={
            "detail": "Item not found",
            "errors": {
                "parameter": "file_uuid",
                "detail": f"File {file_uuid} not found",
            },
        },
    )


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
storage_handler = ElasticsearchStorageHandler(es_client=es, root_index=env.elastic_root_index)


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


@file_app.post("/", tags=["file"], status_code=201)
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


@file_app.get("/", tags=["file"])
async def list_files(user_uuid: Annotated[UUID, Depends(get_user_uuid)]) -> list[File]:
    """Gets a list of files in the database.

    Args:
        user_uuid (UUID): The UUID of the user

    Returns:
        Files (list, File): A list of file objects
    """
    return storage_handler.read_all_items(model_type="File", user_uuid=user_uuid)


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


@file_app.get(
    "/{file_uuid}",
    response_model=File,
    tags=["file"],
    responses={404: {"model": APIError404, "description": "The file was not found"}},
)
def get_file(file_uuid: UUID, user_uuid: Annotated[UUID, Depends(get_user_uuid)]) -> File:
    """Get a file from the object store

    Args:
        file_uuid (UUID): The UUID of the file to get
        user_uuid (UUID): The UUID of the user

    Returns:
        File: The file

    Raises:
        404: If the file isn't found, or the creator and requester don't match
    """
    try:
        file = storage_handler.read_item(file_uuid, model_type="File")
    except NotFoundError:
        return file_not_found_response(file_uuid=file_uuid)

    if file.creator_user_uuid != user_uuid:
        return file_not_found_response(file_uuid=file_uuid)

    return file


@file_app.delete(
    "/{file_uuid}",
    response_model=File,
    tags=["file"],
    responses={404: {"model": APIError404, "description": "The file was not found"}},
)
def delete_file(file_uuid: UUID, user_uuid: Annotated[UUID, Depends(get_user_uuid)]) -> File:
    """Delete a file from the object store and the database

    Args:
        file_uuid (UUID): The UUID of the file to delete
        user_uuid (UUID): The UUID of the user

    Returns:
        File: The file that was deleted

    Raises:
        404: If the file isn't found, or the creator and requester don't match
    """
    try:
        file = storage_handler.read_item(file_uuid, model_type="File")
    except NotFoundError:
        return file_not_found_response(file_uuid=file_uuid)

    if file.creator_user_uuid != user_uuid:
        return file_not_found_response(file_uuid=file_uuid)

    storage_handler.delete_item(file)

    chunks = storage_handler.get_file_chunks(file.uuid, user_uuid)
    storage_handler.delete_items(chunks)
    return file


@file_app.put(
    "/{file_uuid}",
    response_model=File,
    tags=["file"],
    responses={404: {"model": APIError404, "description": "The file was not found"}},
)
async def reingest_file(file_uuid: UUID, user_uuid: Annotated[UUID, Depends(get_user_uuid)]) -> File:
    """Deletes exisiting file chunks and regenerates embeddings

    Args:
        file_uuid (UUID): The UUID of the file to delete
        user_uuid (UUID): The UUID of the user

    Returns:
        File: The file that was deleted

    Raises:
        404: If the file isn't found, or the creator and requester don't match
    """
    try:
        file = storage_handler.read_item(file_uuid, model_type="File")
    except NotFoundError:
        return file_not_found_response(file_uuid=file_uuid)

    if file.creator_user_uuid != user_uuid:
        return file_not_found_response(file_uuid=file_uuid)

    log.info("reingesting %s", file.uuid)

    # Remove old chunks
    chunks = storage_handler.get_file_chunks(file.uuid, user_uuid)
    storage_handler.delete_items(chunks)

    # Add new chunks
    log.info("publishing %s", file.uuid)
    await file_publisher.publish(file)

    return file


@file_app.get(
    "/{file_uuid}/chunks",
    tags=["file"],
    responses={404: {"model": APIError404, "description": "The file was not found"}},
)
def get_file_chunks(file_uuid: UUID, user_uuid: Annotated[UUID, Depends(get_user_uuid)]) -> list[Chunk]:
    """Gets a list of chunks for a file in the database

    Args:
        file_uuid (UUID): The UUID of the file to delete
        user_uuid (UUID): The UUID of the user

    Returns:
        Chunks (list, Chunk): The chunks belonging to the requested file

    Raises:
        404: If the file isn't found, or the creator and requester don't match
    """
    try:
        file = storage_handler.read_item(file_uuid, model_type="File")
    except NotFoundError:
        return file_not_found_response(file_uuid=file_uuid)

    if file.creator_user_uuid != user_uuid:
        return file_not_found_response(file_uuid=file_uuid)

    log.info("getting chunks for file %s", file_uuid)

    return storage_handler.get_file_chunks(file_uuid, user_uuid)


@file_app.get(
    "/{file_uuid}/status",
    tags=["file"],
    responses={404: {"model": APIError404, "description": "The file was not found"}},
)
def get_file_status(file_uuid: UUID, user_uuid: Annotated[UUID, Depends(get_user_uuid)]) -> FileStatus:
    """Get the status of a file

    Args:
        file_uuid (UUID): The UUID of the file to get the status of
        user_uuid (UUID): The UUID of the user

    Returns:
        File: The file with the updated status

    Raises:
        404: If the file isn't found, or the creator and requester don't match
    """
    try:
        file: File = storage_handler.read_item(file_uuid, model_type="File")
    except NotFoundError:
        return file_not_found_response(file_uuid=file_uuid)

    if file.creator_user_uuid != user_uuid:
        return file_not_found_response(file_uuid=file_uuid)

    if file.ingest_status is not None:
        return FileStatus(
            file_uuid=file_uuid,
            # We need to break the link between file status and a specific set of chunks
            # to enable future work with many chunks or other indices etc
            chunk_statuses=[],
            processing_status=file.ingest_status,
        )
    else:
        try:
            return storage_handler.get_file_status(file_uuid, user_uuid)
        except ValueError:
            return file_not_found_response(file_uuid=file_uuid)
