from enum import StrEnum

from pydantic import BaseModel, Field


class ChatRoute(StrEnum):
    search = "search"
    chat = "chat"
    chat_with_docs = "chat/documents"
    chat_with_docs_map_reduce = "chat/documents/large"


class MetadataDetail(BaseModel):
    input_tokens: dict[str, int] = Field(default_factory=dict)
    output_tokens: dict[str, int] = Field(default_factory=dict)
