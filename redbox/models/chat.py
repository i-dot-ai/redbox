from typing import Literal

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


class ChatRequest(BaseModel):
    message_history: list[ChatMessage] = Field(description="The history of messages in the chat")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "message_history": [
                        {"text": "You are a helpful AI Assistant", "role": "system"},
                        {"text": "What is AI?", "role": "user"},
                    ]
                }
            ]
        }
    }


class ChatResponse(BaseModel):
    response_message: ChatMessage = Field(description="The response message")

    model_config = {
        "json_schema_extra": {
            "examples": [{"response_message": {"text": "AI stands for Artificial Intelligence.", "role": "ai"}}]
        }
    }
