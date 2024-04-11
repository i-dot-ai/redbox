import hashlib
from enum import Enum
from typing import Optional
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
    url: AnyUrl = Field(description="s3 url")
    content_type: ContentType = Field(description="content_type of file")
    name: str = Field(description="file name")
    text: Optional[str] = Field(description="file content", default=None)

    @computed_field
    def text_hash(self) -> str:
        return hashlib.md5(
            (self.text or "").encode(encoding="UTF-8", errors="strict"),
            usedforsecurity=False,
        ).hexdigest()

    @computed_field
    def token_count(self) -> int:
        return len(encoding.encode(self.text or ""))

    def to_document(self) -> Document:
        return Document(
            page_content=f"<Doc{self.uuid}>Title: {self.name}\n\n{self.text}</Doc{self.uuid}>\n\n",
            metadata={"source": self.url},
        )


class Chunk(PersistableModel):
    """Chunk of a File"""

    parent_file_uuid: UUID = Field(description="id of the original file which this text came from")
    index: int = Field(description="relative position of this chunk in the original file")
    text: str = Field(description="chunk of the original text")
    metadata: dict
    embedding: Optional[list[float]] = Field(description="the vector representation of the text", default=None)

    @computed_field
    def text_hash(self) -> str:
        return hashlib.md5(self.text.encode(encoding="UTF-8", errors="strict"), usedforsecurity=False).hexdigest()

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
        super().__init__("Document with same name already exists. Please rename if you want to upload anyway.")

    pass
