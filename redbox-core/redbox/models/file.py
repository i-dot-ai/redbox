from __future__ import annotations

from enum import Enum, StrEnum
from uuid import UUID, uuid4
import datetime

from pydantic import BaseModel, Field


class ProcessingStatusEnum(str, Enum):
    """Current status of the file processing.

    Note: The Django app interprets these as:
    "processing" -> "processing"
    "complete" -> "complete"
    "failed" -> "errored"
    anything else -> "processing"

    If you add any other fail state options, the Django app will need to be updated.
    django_app/redbox_app/redbox_core/models.py File.update_status_from_core
    """

    processing = "processing"
    embedding = "embedding"  # Used for processing while we transition to new statuses
    failed = "failed"
    complete = "complete"


class File(BaseModel):
    """Reference to file stored on s3"""

    key: str = Field(description="file key")
    bucket: str = Field(description="s3 bucket")
    creator_user_uuid: UUID


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
    creator_user_uuid: UUID
    index: int
    file_name: str
    page_number: int | None = None
    created_datetime: datetime.datetime = datetime.datetime.now(datetime.UTC)
    token_count: int
    chunk_resolution: ChunkResolution = ChunkResolution.normal
