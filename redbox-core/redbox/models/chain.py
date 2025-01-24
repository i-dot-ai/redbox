from typing import (
    Literal,
    TypedDict,
)

from langchain_core.documents import Document
from pydantic import BaseModel, Field

from redbox.models import prompts
from redbox.models.settings import ChatLLMBackend


class ChainChatMessage(TypedDict):
    role: Literal["user", "ai", "system"]
    text: str


class AISettings(BaseModel):
    """Prompts and other AI settings"""

    # LLM settings
    context_window_size: int = 128_000
    llm_max_tokens: int = 1024

    # Prompts and LangGraph settings
    max_document_tokens: int = 1_000_000
    recursion_limit: int = 50

    # Common Prompt Fragments

    system_info_prompt: str = prompts.SYSTEM_INFO
    persona_info_prompt: str = prompts.PERSONA_INFO
    caller_info_prompt: str = prompts.CALLER_INFO

    # Task Prompt Fragments

    chat_system_prompt: str = prompts.CHAT_SYSTEM_PROMPT
    chat_question_prompt: str = prompts.CHAT_QUESTION_PROMPT
    chat_with_docs_system_prompt: str = prompts.CHAT_WITH_DOCS_SYSTEM_PROMPT
    chat_with_docs_question_prompt: str = prompts.CHAT_WITH_DOCS_QUESTION_PROMPT

    # this is also the azure_openai_model
    chat_backend: ChatLLMBackend = ChatLLMBackend()


class RedboxQuery(BaseModel):
    documents: list[Document] = Field(description="List of files to process", default_factory=list)
    chat_history: list[ChainChatMessage] = Field(description="All previous messages in chat (excluding question)")
    ai_settings: AISettings = Field(description="User request AI settings", default_factory=AISettings)


class RedboxState(BaseModel):
    request: RedboxQuery
