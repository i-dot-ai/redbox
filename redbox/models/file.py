import hashlib
from datetime import datetime
from typing import Dict, Optional
from uuid import uuid4

import tiktoken
from langchain.schema import Document
from pydantic import BaseModel, Field, computed_field

encoding = tiktoken.get_encoding("cl100k_base")


class File(BaseModel):
    uuid: str = Field(default_factory=lambda: str(uuid4()))
    path: str
    type: str
    name: str
    storage_kind: str = "local"
    text: str = ""
    classifications: Optional[Dict] = {}

    created_datetime: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    creator_user_uuid: Optional[str]

    @computed_field
    def model_type(self) -> str:
        return self.__class__.__name__

    @computed_field
    @property
    def text_hash(self) -> str:
        return hashlib.md5(
            self.text.encode(encoding="UTF-8", errors="strict")
        ).hexdigest()

    @computed_field
    @property
    def token_count(self) -> int:
        return len(encoding.encode(self.text))

    def to_document(self) -> str:
        return Document(
            page_content=f"<Doc{self.uuid}>Title: {self.name}\n\n{self.text}</Doc{self.uuid}>\n\n",
            metadata={"source": self.storage_kind},
        )


class Chunk(BaseModel):
    uuid: str = Field(default_factory=lambda: str(uuid4()))
    parent_file_uuid: str
    index: int
    text: str
    metadata: dict

    created_datetime: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    creator_user_uuid: Optional[str]

    @computed_field
    def model_type(self) -> str:
        return self.__class__.__name__

    @computed_field
    @property
    def text_hash(self) -> str:
        return hashlib.md5(
            self.text.encode(encoding="UTF-8", errors="strict")
        ).hexdigest()

    @computed_field
    @property
    def token_count(self) -> int:
        return len(encoding.encode(self.text))


class FileExistsException(Exception):
    def __init__(self):
        super().__init__(
            "Document with same name already exists. Please rename if you want to upload anyway."
        )

    pass
