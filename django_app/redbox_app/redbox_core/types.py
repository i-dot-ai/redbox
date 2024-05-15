from typing import Optional
from uuid import UUID

from redbox_app.redbox_core import models


class ChunkStatus:
    """Status of a chunk of a file."""
    chunk_uuid: UUID
    embedded: bool


class FileStatus:
    file_uuid: UUID
    processing_status: models.ProcessingStatusEnum
    chunk_statuses: Optional[list[ChunkStatus]]

    def __init__(self, file_uuid: UUID, processing_status: models.ProcessingStatusEnum, chunk_statuses: Optional[list[ChunkStatus]] = []):
        self.file_uuid = file_uuid
        self.processing_status = processing_status
        self.chunk_statuses = chunk_statuses
