import hashlib
from enum import Enum
from typing import Optional

import tiktoken
from langchain.schema import Document
from pydantic import computed_field, Field, PositiveInt

from redbox.models.base import PersistableModel

encoding = tiktoken.get_encoding("cl100k_base")


class ProcessingStatusEnum(str, Enum):
    uploaded = "uploaded"
    parsing = "parsing"
    chunking = "chunking"
    embedding = "embedding"
    indexing = "indexing"
    complete = "complete"


class File(PersistableModel):
    path: str
    type: str
    name: str
    storage_kind: str = "local"
    text: str = ""
    processing_status: ProcessingStatusEnum = ProcessingStatusEnum.uploaded

    @computed_field
    def text_hash(self) -> str:
        return hashlib.md5(
            self.text.encode(encoding="UTF-8", errors="strict"), usedforsecurity=False
        ).hexdigest()

    @computed_field
    def token_count(self) -> int:
        return len(encoding.encode(self.text))

    def to_document(self) -> Document:
        return Document(
            page_content=f"<Doc{self.uuid}>Title: {self.name}\n\n{self.text}</Doc{self.uuid}>\n\n",
            metadata={"source": self.storage_kind},
        )


class Chunk(PersistableModel):
    """Chunk of a File"""
    parent_file_uuid: str = Field(description="id of the original file which this text came from")
    index: PositiveInt = Field(description="relative position of this chunk in the original file")
    text: str = Field(description="chunk of the original text")
    metadata: dict
    embedding: Optional[list[float]] = Field(description="the vector representation of the text", default=None)

    @computed_field
    def text_hash(self) -> str:
        return hashlib.md5(
            self.text.encode(encoding="UTF-8", errors="strict"), usedforsecurity=False
        ).hexdigest()

    @computed_field
    def token_count(self) -> int:
        return len(encoding.encode(self.text))


class FileExistsException(Exception):
    def __init__(self):
        super().__init__(
            "Document with same name already exists. Please rename if you want to upload anyway."
        )

    pass
