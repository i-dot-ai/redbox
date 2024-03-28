import logging
from datetime import datetime
from uuid import UUID

from fastapi import FastAPI, UploadFile
from fastapi.responses import RedirectResponse
from faststream.redis.fastapi import RedisRouter

from redbox.model_db import SentenceTransformerDB
from redbox.models import (
    EmbeddingResponse,
    File,
    ModelInfo,
    ProcessingStatusEnum,
    Settings,
    StatusResponse,
    Chunk,
)
from redbox.storage import ElasticsearchStorageHandler

# === Logging ===

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()

env = Settings()
model_db = SentenceTransformerDB(env.embedding_model)


# === Object Store ===

s3 = env.s3_client()


# === Queues ===

router = RedisRouter(url=env.redis_url)

publisher = router.publisher(env.ingest_queue_name)


# === Storage ===

es = env.elasticsearch_client()


storage_handler = ElasticsearchStorageHandler(es_client=es, root_index="redbox-data")


# === API Setup ===

start_time = datetime.now()


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
    lifespan=router.lifespan_context,
)

app.include_router(router)

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

    output = {
        "status": "ready",
        "uptime_seconds": uptime_seconds,
        "version": app.version,
    }

    return output


@app.post("/file", response_model=File, tags=["file"])
async def create_upload_file(file: UploadFile, ingest: bool = True) -> File:
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
        storage_kind=env.object_store,
        processing_status=ProcessingStatusEnum.uploaded,
    )

    storage_handler.write_item(file_record)

    if ingest:
        await ingest_file(file_record.uuid)

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


@app.delete("/file/{file_uuid}", response_model=File, tags=["file"])
def delete_file(file_uuid: UUID) -> File:
    """Delete a file from the object store and the database

    Args:
        file_uuid (str): The UUID of the file to delete

    Returns:
        File: The file that was deleted
    """
    file = storage_handler.read_item(str(file_uuid), model_type="File")
    s3.delete_object(Bucket=env.bucket_name, Key=file.name)
    storage_handler.delete_item(str(file_uuid), model_type="File")
    return file


@app.post("/file/{file_uuid}/ingest", response_model=File, tags=["file"])
async def ingest_file(file_uuid: UUID) -> File:
    """Trigger the ingest process for a file to a queue.

    Args:
        file_uuid (UUID): The UUID of the file to ingest

    Returns:
        File: The file that was ingested
    """
    file = storage_handler.read_item(str(file_uuid), model_type="File")

    file.processing_status = ProcessingStatusEnum.parsing
    storage_handler.update_item(item_uuid=file.uuid, item=file)

    log.info(f"publishing {file.uuid}")
    await publisher.publish(file)

    return file


@app.get("/file/{file_uuid}/chunks", tags=["file"])
def get_file_chunks(file_uuid: UUID) -> list[Chunk]:
    log.info(f"getting chunks for file {file_uuid}")
    return storage_handler.get_file_chunks(file_uuid)


@app.get("/model", tags=["models"])
def get_model() -> ModelInfo:
    """Returns information about the model

    Returns:
        ModelInfo: Information about the model
    """

    return model_db.get_model_info()


@app.post("/embedding", tags=["models"])
def embed_sentences(sentences: list[str]) -> EmbeddingResponse:
    """Embeds a list of sentences using a given model

    Args:
        sentences (list[str]): A list of sentences

    Returns:
        EmbeddingResponse: The embeddings of the sentences
    """

    return model_db.embed_sentences(sentences)
