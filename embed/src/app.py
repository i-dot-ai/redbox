import json
import logging
import threading
from contextlib import asynccontextmanager
from datetime import datetime
from uuid import uuid4

import pydantic
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pika.adapters.blocking_connection import BlockingChannel

from model_db import SentenceTransformerDB
from redbox.models import (
    ModelInfo,
    ModelListResponse,
    EmbeddingResponse,
    EmbedQueueItem,
    StatusResponse,
    Settings,
    Chunk,
)
from redbox.models.llm import Embedding
from redbox.storage import ElasticsearchStorageHandler

start_time = datetime.now()
model_db = SentenceTransformerDB()
log = logging.getLogger()
log.setLevel(logging.INFO)


env = Settings()

es = env.elasticsearch_client()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start of the setup phase
    model_db.init_from_disk()
    thread = threading.Thread(target=subscribe_to_queue)
    thread.start()

    # End of the setup phase, yield control back to FastAPI
    yield
    # FastAPI is shutting down, perform cleanup...
    thread.join()
    log.info("Received shutdown event in the lifespan context, cleaning up.")
    model_db.clear()
    log.info("Cleanup finished, shutting down.")
    log.info("So long, and thanks for all the fish.")


# Create API

app = FastAPI(
    title="Embedding API + Worker",
    description="A simple API that uses sentence-transformers to embed sentence via API calls and from a queue",
    version="0.1.0",
    openapi_tags=[
        {"name": "models", "description": "Get information about the available models"},
        {"name": "health", "description": "Health check"},
    ],
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
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

    output = {
        "status": ("ready" if model_db else "loading"),
        "uptime_seconds": uptime_seconds,
        "version": app.version,
    }

    return output


# Models and Embeddings


@app.get("/models", response_model=ModelListResponse, tags=["models"])
def get_models():
    """Returns a list of available models

    Returns:
        ModelListResponse: A list of available models
    """
    return {"models": [model_db.get_model_info(m) for m in model_db]}


@app.get("/models/{model}", response_model=ModelInfo, tags=["models"])
def get_model(model: str):
    """Returns information about a given model

    Args:
        model (str): The name of the model

    Returns:
        ModelInfo: Information about the model
    """

    if model not in model_db:
        raise HTTPException(status_code=404, detail=f"Model {model} not found")
    return model_db.get_model_info(model)


@app.post("/models/{model}/embed", tags=["models"])
def embed_sentences(model: str, sentences: list[str]) -> EmbeddingResponse:
    """Embeds a list of sentences using a given model

    Args:
        model (str): The name of the model
        sentences (list[str]): A list of sentences

    Returns:
        EmbeddingResponse: The embeddings of the sentences
    """

    if model not in model_db:
        raise HTTPException(status_code=404, detail=f"Model {model} not found")

    model_obj = model_db[model]
    embeddings = model_obj.encode(sentences)

    reformatted_embeddings = [
        Embedding(
            object="embedding",
            index=i,
            embedding=list(embedding),
        )
        for i, embedding in enumerate(embeddings)
    ]

    output = EmbeddingResponse(
        object="list",
        data=reformatted_embeddings,
        embedding_id=str(uuid4()),
        model=model,
        model_info=model_db.get_model_info(model),
    )

    return output


def subscribe_to_queue():
    connection = env.blocking_connection()
    channel = connection.channel()
    channel.queue_declare(queue=env.embed_queue_name, durable=True)
    storage_handler = ElasticsearchStorageHandler(es_client=es, root_index="redbox-data")
    chunk_embedder = ChunkEmbedder(storage_handler)

    channel.basic_consume(queue=env.embed_queue_name, on_message_callback=chunk_embedder.callback, auto_ack=False)
    channel.start_consuming()


class ChunkEmbedder:
    def __init__(self, storage_handler: ElasticsearchStorageHandler):
        self.storage_handler = storage_handler

    def embed_queue_item(self, queue_item: EmbedQueueItem):
        """
        1. embed queue-item text
        2. update related chunk on ES
        """

        embedded_sentences = embed_sentences(queue_item.model, [queue_item.sentence])
        chunk: Chunk = self.storage_handler.read_item(queue_item.chunk_uuid, "Chunk")
        if len(embedded_sentences.data) != 1:
            raise ValueError(f"expected just 1 embedding but got {len(embedded_sentences.data)}")
        chunk.embedding = embedded_sentences.data[0].embedding
        self.storage_handler.update_item(queue_item.chunk_uuid, chunk)

    def callback(self, ch: BlockingChannel, method, properties, body):
        logging.info(f"Received message {method.delivery_tag} by callback")
        try:
            body_dict = json.loads(body.decode("utf-8"))
            embed_queue_item = EmbedQueueItem(**body_dict)
            self.embed_queue_item(embed_queue_item)
        except json.JSONDecodeError as e:
            logging.error(f"Failed to decode message: {e}")
        except pydantic.ValidationError as e:
            logging.error(f"Failed to validate message: {e}")
        finally:
            ch.basic_ack(delivery_tag=method.delivery_tag)
