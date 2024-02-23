import json
import logging
import os
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime
from uuid import uuid4

import pika
import pydantic
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from sentence_transformers import SentenceTransformer

# === Data Models ===


class ModelInfo(pydantic.BaseModel):
    model: str
    max_seq_length: int
    vector_size: int


class Embedding(pydantic.BaseModel):
    object: str = "embedding"
    index: int
    embedding: list[float]


class EmbeddingResponse(pydantic.BaseModel):
    object: str = "list"
    data: list[Embedding]
    embedding_id: str
    model: str
    model_info: ModelInfo


class EmbeddingRequest(pydantic.BaseModel):
    sentences: list[str]


class ModelListResponse(pydantic.BaseModel):
    models: list[ModelInfo]


class StatusResponse(pydantic.BaseModel):
    status: str
    uptime_seconds: float
    version: str


class EmbedQueueItem(pydantic.BaseModel):
    model: str
    sentence: str


def get_model_info(model_name: str) -> ModelInfo:
    model_obj = models[model_name]
    model_info_entry = ModelInfo(
        model=model_name,
        max_seq_length=model_obj.get_max_seq_length(),
        vector_size=model_obj.get_sentence_embedding_dimension(),
    )
    return model_info_entry


# === API Setup ===


start_time = datetime.now()
IS_READY = False
available_models = []
models = {}
log = logging.getLogger()
log.setLevel(logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global IS_READY
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
        log.info(f"Loaded model {model}")

    IS_READY = True

    # Check to see if we run in polling mode from a queue
    if "QUEUE_URI" in os.environ:
        log.info("Queue URI found, starting queue listener.")
        queue_uri = os.environ["QUEUE_URI"]
        queue_name = os.environ.get("EMBED_QUEUE_NAME", "redbox-embed-queue")
        queue_poll_interval = int(os.environ.get("QUEUE_POLL_INTERVAL", 5))

        poll_thread = threading.Thread(
            target=poll_queue_every, args=(queue_uri, queue_name, queue_poll_interval)
        )
        poll_thread.start()

    # End of the setup phase, yield control back to FastAPI
    yield
    # FastAPI is shutting down, perform cleanup...
    if poll_thread is not None:
        poll_thread.join()
    log.info("Received shutdown event in the lifespan context, cleaning up.")
    IS_READY = False
    models.clear()
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

    output = {"status": None, "uptime_seconds": uptime_seconds, "version": app.version}

    if IS_READY:
        output["status"] = "ready"
    else:
        output["status"] = "loading"

    return output


# Models and Embeddings


@app.get("/models", response_model=ModelListResponse, tags=["models"])
def get_models():
    """Returns a list of available models

    Returns:
        ModelListResponse: A list of available models
    """
    return {"models": [get_model_info(m) for m in models]}


@app.get("/models/{model}", response_model=ModelInfo, tags=["models"])
def get_model(model: str):
    """Returns information about a given model

    Args:
        model (str): The name of the model

    Returns:
        ModelInfo: Information about the model
    """

    if model not in models:
        raise HTTPException(status_code=404, detail=f"Model {model} not found")
    return get_model_info(model)


@app.post("/models/{model}/embed", response_model=EmbeddingResponse, tags=["models"])
def embed_sentences(model: str, sentences: list[str]):
    """Embeds a list of sentences using a given model

    Args:
        model (str): The name of the model
        sentences (list[str]): A list of sentences

    Returns:
        EmbeddingResponse: The embeddings of the sentences
    """

    if model not in models:
        raise HTTPException(status_code=404, detail=f"Model {model} not found")

    model_obj = models[model]
    embeddings = model_obj.encode(sentences)

    reformatted_embeddings = []

    for i, embedding in enumerate(embeddings):
        new_embedding = {
            "object": "embedding",
            "index": i,
            "embedding": list(embedding),
        }
        reformatted_embeddings.append(new_embedding)

    output = {
        "object": "list",
        "data": reformatted_embeddings,
        "embedding_id": str(uuid4()),
        "model": model,
        "model_info": get_model_info(model),
    }

    return output


def poll_queue_every(queue_uri: str, queue_name: str, interval: int = 5):
    logging.debug(f"Starting queue poller for {queue_name} every {interval} seconds")
    while True:
        logging.debug(f"Polling queue {queue_name} (every {interval} seconds)")
        poll_queue(queue_uri, queue_name)
        time.sleep(interval)


def poll_queue(queue_uri: str, queue_name: str, max_connection_attempts: int = 10):
    logging.info(f"Polling queue {queue_name}")

    connection = None

    for i in range(max_connection_attempts):
        try:
            logging.debug(
                f"Attempting to connect to queue {queue_name} (attempt {i}/{max_connection_attempts})"
            )
            connection = pika.BlockingConnection(
                parameters=pika.URLParameters(queue_uri),
            )
            logging.debug(f"Connected to queue {queue_name}")
            break
        except Exception as e:
            logging.error(f"Failed to connect to queue attempt {i}: {e}")
            time.sleep(5)

    if not connection:
        logging.error("Failed to connect to queue, shutting down")
        return

    channel = connection.channel()
    channel.queue_declare(queue=queue_name, durable=True)
    channel.basic_consume(
        queue=queue_name, on_message_callback=embed_item_callback, auto_ack=False
    )
    channel.start_consuming()


def embed_item_callback(ch, method, properties, body):
    logging.info(f"Received message {method.delivery_tag} by callback")

    try:
        body_dict = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as e:
        logging.error(f"Failed to decode message: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag)
        return
    try:
        embed_queue_item = EmbedQueueItem(**body_dict)
    except pydantic.ValidationError as e:
        logging.error(f"Failed to validate message: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag)
        return

    output = embed_sentences(embed_queue_item.model, [embed_queue_item.sentence])
    output = EmbeddingResponse(**output)

    # TODO: Send the output to Elasticsearch?

    logging.info(
        f"Embedding ID {output.embedding_id} complete for {method.delivery_tag}"
    )
    ch.basic_ack(delivery_tag=method.delivery_tag)
    ch.stop_consuming()
