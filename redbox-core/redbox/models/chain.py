from typing import TypedDict
from langchain_core.pydantic_v1 import BaseModel, Field

from redbox.models.chat import ChatMessage
from redbox.models.file import UUID


class ChainChatMessage(TypedDict):
    role: str
    text: str

class ChainInput(BaseModel):
    question: str = Field(description="The last user chat message")
    file_uuids: list[str] = Field(description="List of files to process")
    user_uuid: str = Field(description="User the chain in executing for")
    chat_history: list[ChainChatMessage] = Field(description="All previous messages in chat (excluding question)")