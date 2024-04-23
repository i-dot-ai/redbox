from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    text: str = Field(description="The text of the message")
    role: Literal["user", "ai", "system"] = Field(description="The role of the message")


class ChatRequest(BaseModel):
    message_history: list[ChatMessage] = Field(description="The history of messages in the chat")


class ChatResponse(BaseModel):
    response_message: ChatMessage = Field(description="The response message")
