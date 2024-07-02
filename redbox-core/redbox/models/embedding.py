from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class EmbeddingModelInfo(BaseModel):
    """Information about the model used to generate the embeddings"""

    embedding_model: str
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
    embedding_model: str
    embedding_model_info: EmbeddingModelInfo


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
