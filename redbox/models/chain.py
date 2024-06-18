from pydantic import BaseModel, Field

from redbox.models.chat import ChatMessage
from redbox.models.file import UUID


class ChainInput(BaseModel):
    question: str = Field(description="The last user chat message")
    file_uuids: list[UUID] = Field(description="List of files to process")
    user_uuid: UUID = Field(description="User the chain in executing for")
    chat_history: list[ChatMessage] = Field(description="All previous messages in chat (excluding question)")
