import logging
from datetime import datetime
<<<<<<< HEAD
from uuid import UUID
=======
>>>>>>> 33ebdf6 (create file sub app)

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from faststream.redis.fastapi import RedisRouter

# from sub_apps.file import file_app
from file import FileSubApp

from redbox.model_db import SentenceTransformerDB
from redbox.models import EmbeddingResponse, ModelInfo, Settings, StatusResponse
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


file_app = FileSubApp(router, storage_handler, log, publisher, s3, env)
app.include_router(file_app.router)

log.info(app.router.__dict__)
