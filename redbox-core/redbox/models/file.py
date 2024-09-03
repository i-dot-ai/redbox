from __future__ import annotations

from enum import StrEnum
from uuid import UUID, uuid4
import datetime

from pydantic import BaseModel, Field


class ChunkResolution(StrEnum):
    smallest = "smallest"
    small = "small"
    normal = "normal"
    large = "large"
    largest = "largest"


class ChunkMetadata(BaseModel):
    """
    Worker model for document metadata for new style chunks.
    This is the minimal metadata that all ingest chains provide and should not be used to map retrieved documents (as fields will be lost)
    """

    uuid: UUID = Field(default_factory=uuid4)
    index: int
    file_name: str
    page_number: int | None = None
    created_datetime: datetime.datetime = datetime.datetime.now(datetime.UTC)
    token_count: int
    chunk_resolution: ChunkResolution = ChunkResolution.normal
