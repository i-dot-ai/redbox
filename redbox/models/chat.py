from typing import Optional

from langchain.chains.base import Chain
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from pydantic import field_serializer, Field, BaseModel

from redbox.models.base import PersistableModel


class ChatMessage(PersistableModel):
    # langchain.chains.base.Chain needs pydantic v1, breaks
    # https://python.langchain.com/docs/guides/pydantic_compatibility
    chain: Optional[object] = None
    message: object

    @field_serializer("chain")
    def serialise_chain(self, chain: Chain, _info):
        if isinstance(chain, Chain):
            return chain.dict()
        else:
            return chain

    @field_serializer("message")
    def serialise_message(self, message: AIMessage | HumanMessage | SystemMessage, _info):
        if isinstance(message, (AIMessage, HumanMessage, SystemMessage)):
            return message.dict()
        else:
            return message


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
