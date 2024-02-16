import hashlib

import tiktoken
from langchain.schema import Document
from pydantic import computed_field

from redbox.models.base import PersistableModel

encoding = tiktoken.get_encoding("cl100k_base")


class File(PersistableModel):
    path: str
    type: str
    name: str
    storage_kind: str = "local"
    text: str = ""

    @computed_field
    def model_type(self) -> str:
        return self.__class__.__name__

    @property
    @computed_field
    def text_hash(self) -> str:
        return hashlib.md5(
            self.text.encode(encoding="UTF-8", errors="strict")
        ).hexdigest()

    @property
    @computed_field
    def token_count(self) -> int:
        return len(encoding.encode(self.text))

    def to_document(self) -> Document:
        return Document(
            page_content=f"<Doc{self.uuid}>Title: {self.name}\n\n{self.text}</Doc{self.uuid}>\n\n",
            metadata={"source": self.storage_kind},
        )


class Chunk(PersistableModel):
    parent_file_uuid: str
    index: int
    text: str
    metadata: dict

    @computed_field
    def model_type(self) -> str:
        return self.__class__.__name__

    @property
    @computed_field
    def text_hash(self) -> str:
        return hashlib.md5(
            self.text.encode(encoding="UTF-8", errors="strict")
        ).hexdigest()

    @property
    @computed_field
    def token_count(self) -> int:
        return len(encoding.encode(self.text))


class FileExistsException(Exception):
    def __init__(self):
        super().__init__(
            "Document with same name already exists. Please rename if you want to upload anyway."
        )

    pass
