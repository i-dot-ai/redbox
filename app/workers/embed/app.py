import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from uuid import uuid4

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


# === API Setup ===


start_time = datetime.now()
IS_READY = False
available_models = []
models = {}
model_info = {}
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


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

    for model, model_obj in models.items():
        model_info_entry = {
            "model": model,
            "max_seq_length": model_obj.get_max_seq_length(),
            "vector_size": model_obj.get_sentence_embedding_dimension(),
        }

        model_info[model] = model_info_entry

    IS_READY = True
    # End of the setup phase, yield control back to FastAPI
    yield
    # FastAPI is shutting down, perform cleanup...
    log.info("Received shutdown event in the lifespan context, cleaning up.")
    IS_READY = False
    models.clear()
    model_info.clear()
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
    return {"models": list(model_info.values())}


@app.get("/models/{model}", response_model=ModelInfo, tags=["models"])
def get_model(model: str):
    """Returns information about a given model

    Args:
        model (str): The name of the model

    Returns:
        ModelInfo: Information about the model
    """

    if model not in model_info:
        raise HTTPException(status_code=404, detail=f"Model {model} not found")

    return model_info[model]


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
        "model_info": model_info[model],
    }

    return output
