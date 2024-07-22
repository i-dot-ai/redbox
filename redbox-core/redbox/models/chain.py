"""
There is some repeated definition and non-pydantic style code in here.
These classes are pydantic v1 which is compatible with langchain tools classes, we need
to provide a pydantic v1 definition to work with these. As these models are mostly
used in conjunction with langchain this is the tidiest boxing of pydantic v1 we can do
"""

from typing import TypedDict, Literal
from uuid import UUID
from langchain_core.pydantic_v1 import BaseModel, Field


class ChainChatMessage(TypedDict):
    role: Literal["user", "ai", "system"]
    text: str


class ChainInput(BaseModel):
    question: str = Field(description="The last user chat message")
    file_uuids: list[UUID] = Field(description="List of files to process")
    user_uuid: UUID = Field(description="User the chain in executing for")
    chat_history: list[ChainChatMessage] = Field(description="All previous messages in chat (excluding question)")
