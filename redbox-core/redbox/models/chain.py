from langchain_core.documents import Document
from langchain_core.messages import AnyMessage
from pydantic import BaseModel, Field

from redbox.models.settings import ChatLLMBackend


class AISettings(BaseModel):
    """Prompts and other AI settings"""

    # LLM settings
    context_window_size: int = 128_000

    # this is also the azure_openai_model
    chat_backend: ChatLLMBackend = ChatLLMBackend()


class RedboxState(BaseModel):
    documents: list[Document] = Field(description="List of files to process", default_factory=list)
    messages: list[AnyMessage] = Field(description="All previous messages in chat", default_factory=list)
    ai_settings: AISettings = Field(description="User request AI settings", default_factory=AISettings)
