from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class ModelInfo(BaseModel):
    model: str
    max_seq_length: int
    vector_size: int


class Embedding(BaseModel):
    object: Literal["embedding"]
    index: int
    embedding: list[float]


class EmbeddingResponse(BaseModel):
    object: Literal["list"]
    data: list[Embedding]
    embedding_id: str
    model: str
    model_info: ModelInfo


class EmbeddingRequest(BaseModel):
    sentences: list[str]


class ModelListResponse(BaseModel):
    models: list[ModelInfo]


class StatusResponse(BaseModel):
    status: str
    uptime_seconds: float
    version: str


class EmbedQueueItem(BaseModel):
    model: str
    sentence: str
    chunk_uuid: str
