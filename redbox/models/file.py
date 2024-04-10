import hashlib
from enum import Enum
from typing import Optional
from urllib.parse import unquote
from uuid import UUID

import tiktoken
from langchain.schema import Document
from pydantic import AnyUrl, BaseModel, Field, computed_field

from redbox.models.base import PersistableModel

encoding = tiktoken.get_encoding("cl100k_base")


class ProcessingStatusEnum(str, Enum):
    chunking = "chunking"
    embedding = "embedding"
    complete = "complete"


class ContentType(str, Enum):
    EML = ".eml"
    HTML = ".html"
    HTM = ".htm"
    JSON = ".json"
    MD = ".md"
    MSG = ".msg"
    RST = ".rst"
    RTF = ".rtf"
    TXT = ".txt"
    XML = ".xml"
    JPEG = ".jpeg"  # Must have tesseract installed
    PNG = ".png"  # Must have tesseract installed
    CSV = ".csv"
    DOC = ".doc"
    DOCX = ".docx"
    EPUB = ".epub"
    ODT = ".odt"
    PDF = ".pdf"
    PPT = ".ppt"
    PPTX = ".pptx"
    TSV = ".tsv"
    XLSX = ".xlsx"


class File(PersistableModel):
    """This is a reference to file stored in S3"""
    url: AnyUrl = Field(description="s3 url")
    _bucket: str
    _key: str
    _extension: str

    @computed_field
    def bucket(self) -> str:
        return self._bucket

    @computed_field
    def key(self) -> str:
        return self._key

    @computed_field
    def extension(self) -> str:
        return self._extension

    def __init__(self, **data):
        super().__init__(**data)
        url = unquote(str(self.url))
        bucket, key = url.split("/", 2)[-1].split("/", 1)
        self._bucket = bucket[:-len(".s3.amazonaws.com")]
        self._key = key
        self._extension = "." + key.split(".")[-1]



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
