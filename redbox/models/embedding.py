from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ModelInfo(BaseModel):
    """Information about the model used to generate the embeddings"""

    model: str
    max_seq_length: int
    vector_size: int


class Embedding(BaseModel):
    """Embedding of a piece of text"""

    object: Literal["embedding"]
    index: int
    embedding: list[float]


class EmbeddingResponse(BaseModel):
    """Response from the embedding service in OpenAI format"""

    object: Literal["list"]
    data: list[Embedding]
    embedding_id: str
    model: str
    model_info: ModelInfo


class EmbeddingRequest(BaseModel):
    """Request to the embedding service."""

    sentences: list[str]


class StatusResponse(BaseModel):
    status: str
    uptime_seconds: float
    version: str


class EmbedQueueItem(BaseModel):
    """Instruction to Ingest app for what to embed"""

    chunk_uuid: UUID = Field(description="id of the chunk that this text belongs to")


class EmbeddingModelInfo(BaseModel):
    """Information about the model used to generate the embeddings"""

    model: str
    vector_size: int
