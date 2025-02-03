from uuid import UUID

from langchain_core.documents import Document
from langchain_core.messages import AnyMessage
from pydantic import BaseModel, Field

from redbox.models.settings import ChatLLMBackend


class RedboxState(BaseModel):
    user_uuid: UUID = Field(description="UUID of the user making the request")
    documents: list[Document] = Field(description="List of files to process", default_factory=list)
    messages: list[AnyMessage] = Field(description="All previous messages in chat", default_factory=list)
    chat_backend: ChatLLMBackend = Field(description="User request AI settings", default_factory=ChatLLMBackend)
