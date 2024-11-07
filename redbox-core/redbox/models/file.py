from __future__ import annotations

import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import AliasChoices, BaseModel, Field


class ChunkResolution(StrEnum):
    smallest = "smallest"
    small = "small"
    normal = "normal"
    large = "large"
    largest = "largest"


class ChunkCreatorType(StrEnum):
    wikipedia = "Wikipedia"
    user_uploaded_document = "UserUploadedDocument"
    gov_uk = "GOV.UK"


class ChunkMetadata(BaseModel):
    """
    Worker model for document metadata for new style chunks.
    This is the minimal metadata that all ingest chains provide and should not be used to map retrieved documents (as fields will be lost)
    """

    uuid: UUID = Field(default_factory=uuid4)
    index: int = 0  # The order of this chunk in the original resource
    created_datetime: datetime.datetime = datetime.datetime.now(datetime.UTC)
    chunk_resolution: ChunkResolution = ChunkResolution.normal
    creator_type: ChunkCreatorType
    uri: str = Field(validation_alias=AliasChoices("uri", "file_name"))  # URL or file name
    token_count: int


class UploadedFileMetadata(ChunkMetadata):
    """
    Model for uploaded document chunk metadata.
    """

    page_number: int | None = None
    name: str | None = None
    description: str | None = None
    keywords: list[str] | None = None
    creator_type: ChunkCreatorType = ChunkCreatorType.user_uploaded_document
