import hashlib
from enum import Enum
from typing import Optional
from uuid import UUID

import tiktoken
from pydantic import BaseModel, Field, computed_field

from redbox.models.base import PersistableModel

encoding = tiktoken.get_encoding("cl100k_base")


class ProcessingStatusEnum(str, Enum):
    chunking = "chunking"
    embedding = "embedding"
    complete = "complete"


class File(PersistableModel):
    """This is a reference to file stored in S3"""
    key: str
    _extension: str

    @computed_field
    def extension(self) -> str:
        return "." + self.key.split(".")[-1]

    def generate_presigned_url(self, bucket:str, s3_client) -> str:
        url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket":bucket, "Key": self.key},
            ExpiresIn=3600,
        )
        return url



class Chunk(PersistableModel):
    """Chunk of a File"""

    parent_file_uuid: UUID = Field(
        description="id of the original file which this text came from"
    )
    index: int = Field(
        description="relative position of this chunk in the original file"
    )
    text: str = Field(description="chunk of the original text")
    metadata: dict
    embedding: Optional[list[float]] = Field(
        description="the vector representation of the text", default=None
    )

    @computed_field
    def text_hash(self) -> str:
        return hashlib.md5(
            self.text.encode(encoding="UTF-8", errors="strict"), usedforsecurity=False
        ).hexdigest()

    @computed_field
    def token_count(self) -> int:
        return len(encoding.encode(self.text))


class ChunkStatus(BaseModel):
    chunk_uuid: UUID
    embedded: bool


class FileStatus(BaseModel):
    file_uuid: UUID
    processing_status: ProcessingStatusEnum
    chunk_statuses: Optional[list[ChunkStatus]]


class FileExistsException(Exception):
    def __init__(self):
        super().__init__(
            "Document with same name already exists. Please rename if you want to upload anyway."
        )

    pass
