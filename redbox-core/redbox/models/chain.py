from enum import StrEnum
from typing import (
    Annotated,
    Literal,
    TypedDict,
)
from uuid import UUID

from langchain_core.documents import Document
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
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
    question: str = Field(description="The last user chat message")
    documents: list[Document] = Field(description="List of files to process", default_factory=list)
    user_uuid: UUID = Field(description="User the chain in executing for")
    chat_history: list[ChainChatMessage] = Field(description="All previous messages in chat (excluding question)")
    ai_settings: AISettings = Field(description="User request AI settings", default_factory=AISettings)


class RedboxState(BaseModel):
    request: RedboxQuery
    messages: Annotated[list[AnyMessage], add_messages] = Field(default_factory=list)


class PromptSet(StrEnum):
    Chat = "chat"
    ChatwithDocs = "chat_with_docs"


def get_prompts(state: RedboxState, prompt_set: PromptSet) -> tuple[str, str]:
    if prompt_set == PromptSet.Chat:
        system_prompt = state.request.ai_settings.chat_system_prompt
        question_prompt = state.request.ai_settings.chat_question_prompt
    elif prompt_set == PromptSet.ChatwithDocs:
        system_prompt = state.request.ai_settings.chat_with_docs_system_prompt
        question_prompt = state.request.ai_settings.chat_with_docs_question_prompt
    return (system_prompt, question_prompt)
