from datetime import UTC, datetime
from enum import StrEnum
from functools import reduce
from typing import (
    Annotated,
    Literal,
    TypedDict,
)
from uuid import UUID, uuid4

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
    question: str = Field(description="The last user chat message")
    s3_keys: list[str] = Field(description="List of files to process", default_factory=list)
    user_uuid: UUID = Field(description="User the chain in executing for")
    chat_history: list[ChainChatMessage] = Field(description="All previous messages in chat (excluding question)")
    ai_settings: AISettings = Field(description="User request AI settings", default_factory=AISettings)
    permitted_s3_keys: list[str] = Field(description="List of permitted files for response", default_factory=list)


class LLMCallMetadata(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    llm_model_name: str
    input_tokens: int
    output_tokens: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = {"frozen": True}


class RequestMetadata(BaseModel):
    llm_calls: list[LLMCallMetadata] = Field(default_factory=list)
    selected_files_total_tokens: int = 0
    number_of_selected_files: int = 0

    @property
    def input_tokens(self) -> dict[str, int]:
        """
        Creates a dictionary of model names to number of input tokens used
        """
        tokens_by_model = dict()
        for call_metadata in self.llm_calls:
            tokens_by_model[call_metadata.llm_model_name] = (
                tokens_by_model.get(call_metadata.llm_model_name, 0) + call_metadata.input_tokens
            )
        return tokens_by_model

    @property
    def output_tokens(self):
        """
        Creates a dictionary of model names to number of output tokens used
        """
        tokens_by_model = dict()
        for call_metadata in self.llm_calls:
            tokens_by_model[call_metadata.llm_model_name] = (
                tokens_by_model.get(call_metadata.llm_model_name, 0) + call_metadata.output_tokens
            )
        return tokens_by_model


def metadata_reducer(
    current: RequestMetadata | None,
    update: RequestMetadata | list[RequestMetadata] | None,
):
    """Merges two metadata states."""
    # If update is actually a list of state updates, run them one by one
    if isinstance(update, list):
        reduced = reduce(lambda current, update: metadata_reducer(current, update), update, current)
        return reduced

    if current is None:
        return update
    if update is None:
        return current

    return RequestMetadata(
        llm_calls=sorted(set(current.llm_calls) | set(update.llm_calls), key=lambda c: c.timestamp),
        selected_files_total_tokens=update.selected_files_total_tokens or current.selected_files_total_tokens,
        number_of_selected_files=update.number_of_selected_files or current.number_of_selected_files,
    )


class RedboxState(BaseModel):
    request: RedboxQuery
    documents: list[Document] = Field(default_factory=list)
    route_name: str | None = None
    metadata: Annotated[RequestMetadata | None, metadata_reducer] = None
    messages: Annotated[list[AnyMessage], add_messages] = Field(default_factory=list)

    @property
    def last_message(self) -> AnyMessage:
        if not self.messages:
            raise ValueError("No messages in the state")
        return self.messages[-1]


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
