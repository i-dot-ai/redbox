from enum import StrEnum
from typing import Literal

from redbox.models.chain import AISettings
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    text: str = Field(description="The text of the message")
    role: Literal["user", "ai", "system"] = Field(description="The role of the message")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"text": "You are helpful AI Assistant", "role": "system"},
                {"text": "Hello", "role": "user"},
                {"text": "Hi there!", "role": "ai"},
            ]
        }
    }


class SelectedDocument(BaseModel):
    s3_key: str = Field(description="s3_key of selected file")


class ChatRequest(BaseModel):
    message_history: list[ChatMessage] = Field(description="The history of messages in the chat")
    selected_files: list[SelectedDocument] = Field(
        description="Documents selected to use for the current chat request",
        default_factory=list,
    )
    ai_settings: AISettings = Field(default_factory=AISettings)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "message_history": [
                        {"text": "You are a helpful AI Assistant", "role": "system"},
                        {"text": "What is AI?", "role": "user"},
                    ],
                    "selected_files": [
                        {"s3_key": "s3_key_1"},
                        {"s3_key": "s3_key_2"},
                    ],
                }
            ]
        }
    }


class SourceDocument(BaseModel):
    page_content: str = Field(description="chunk text")
    s3_key: str = Field(description="s3_key of original file")
    page_numbers: list[int] | None = Field(
        description="page number of the file that this chunk came from", default=None
    )


class SourceDocuments(BaseModel):
    source_documents: list[SourceDocument] | None = Field(
        description="documents retrieved to form this response", default=None
    )


class ChatRoute(StrEnum):
    search = "search"
    chat = "chat"
    chat_with_docs = "chat/documents"
    chat_with_docs_map_reduce = "chat/documents/large"


class ChatResponse(BaseModel):
    source_documents: list[SourceDocument] | None = Field(
        description="documents retrieved to form this response", default=None
    )
    output_text: str = Field(
        description="response text",
        examples=["The current Prime Minister of the UK is The Rt Hon. Rishi Sunak MP."],
    )
    route_name: ChatRoute = Field(description="the conversation route taken")


class MetadataDetail(BaseModel):
    input_tokens: dict[str, int] = Field(default_factory=dict)
    output_tokens: dict[str, int] = Field(default_factory=dict)


class ErrorDetail(BaseModel):
    code: str
    message: str


class ClientResponse(BaseModel):
    # Needs to match CoreChatResponse in django_app/redbox_app/redbox_core/consumers.py
    resource_type: str
    data: list[SourceDocument] | str | MetadataDetail | ErrorDetail | None = None
