from datetime import UTC, datetime
from enum import StrEnum
from functools import reduce
from typing import (
    Annotated,
    Literal,
    NotRequired,
    Required,
    TypedDict,
    get_args,
    get_origin,
)
from uuid import UUID, uuid4

from langchain_core.documents import Document
from langchain_core.messages import ToolCall
from langgraph.managed.is_last_step import RemainingSteps
from pydantic import BaseModel, Field

from redbox.models import prompts


class ChainChatMessage(TypedDict):
    role: Literal["user", "ai", "system"]
    text: str


class ChatLLMBackend(BaseModel):
    name: str = "gpt-4o"
    provider: str = "azure_openai"
    description: str | None = None
    model_config = {"frozen": True}


class AISettings(BaseModel):
    """Prompts and other AI settings"""

    # LLM settings
    context_window_size: int = 128_000
    llm_max_tokens: int = 1024

    # Prompts and LangGraph settings
    max_document_tokens: int = 1_000_000
    self_route_enabled: bool = False
    map_max_concurrency: int = 128
    stuff_chunk_context_ratio: float = 0.75
    recursion_limit: int = 50

    chat_system_prompt: str = prompts.CHAT_SYSTEM_PROMPT
    chat_question_prompt: str = prompts.CHAT_QUESTION_PROMPT
    chat_with_docs_system_prompt: str = prompts.CHAT_WITH_DOCS_SYSTEM_PROMPT
    chat_with_docs_question_prompt: str = prompts.CHAT_WITH_DOCS_QUESTION_PROMPT
    chat_with_docs_reduce_system_prompt: str = prompts.CHAT_WITH_DOCS_REDUCE_SYSTEM_PROMPT
    self_route_system_prompt: str = prompts.SELF_ROUTE_SYSTEM_PROMPT
    retrieval_system_prompt: str = prompts.RETRIEVAL_SYSTEM_PROMPT
    retrieval_question_prompt: str = prompts.RETRIEVAL_QUESTION_PROMPT
    agentic_retrieval_system_prompt: str = prompts.AGENTIC_RETRIEVAL_SYSTEM_PROMPT
    agentic_retrieval_question_prompt: str = prompts.AGENTIC_RETRIEVAL_QUESTION_PROMPT
    agentic_give_up_system_prompt: str = prompts.AGENTIC_GIVE_UP_SYSTEM_PROMPT
    agentic_give_up_question_prompt: str = prompts.AGENTIC_GIVE_UP_QUESTION_PROMPT
    condense_system_prompt: str = prompts.CONDENSE_SYSTEM_PROMPT
    condense_question_prompt: str = prompts.CONDENSE_QUESTION_PROMPT
    chat_map_system_prompt: str = prompts.CHAT_MAP_SYSTEM_PROMPT
    chat_map_question_prompt: str = prompts.CHAT_MAP_QUESTION_PROMPT
    reduce_system_prompt: str = prompts.REDUCE_SYSTEM_PROMPT

    # Elasticsearch RAG and boost values
    rag_k: int = 30
    rag_num_candidates: int = 10
    rag_gauss_scale_size: int = 3
    rag_gauss_scale_decay: float = 0.5
    rag_gauss_scale_min: float = 1.1
    rag_gauss_scale_max: float = 2.0
    elbow_filter_enabled: bool = False
    match_boost: float = 1.0
    match_name_boost: float = 2.0
    match_description_boost: float = 0.5
    match_keywords_boost: float = 0.5
    knn_boost: float = 2.0
    similarity_threshold: float = 0.7

    # this is also the azure_openai_model
    chat_backend: ChatLLMBackend = ChatLLMBackend()


class Source(BaseModel):
    source: str = Field(description="URL or reference to the source")
    last_edited: str = ""
    document_name: str = ""
    highlighted_text: str = ""
    page_no: str = Field(description="")


class Citation(BaseModel):
    text: str
    sources: list[Source]


class LLM_Response(BaseModel):
    markdown_answer: str
    citations: list[Citation]

    @classmethod
    def model_json_schema(self):
        return {
            "markdown_answer": "Hello Kitty is a fictional character from Japan.",
            "citations": [
                {
                    "text": "Hello Kitty is a fictional character from Japan.",
                    "sources": [
                        {
                            "source": "https://en.wikipedia.org/wiki/Hello_Kitty",
                            "last_edited": "4 October 2024",
                            "document_name": "Hello Kitty",
                            "highlighted_text": "Hello Kitty (Japanese: ハロー・キティ, Hepburn: Harō Kiti),[6] also known by her real name Kitty White (キティ・ホワイト, Kiti Howaito),[5] is a fictional character created by Yuko Shimizu",
                            "page_no": "1",
                        }
                    ],
                }
            ],
        }


class DocumentState(TypedDict):
    group: dict[UUID, Document]


def document_reducer(current: DocumentState | None, update: DocumentState | list[DocumentState]) -> DocumentState:
    """Merges two document states based on the following rules.

    * Groups are matched by the group key.
    * Documents are matched by the group key and document key.

    Then:

    * If key(s) are matched, the group or Document is replaced
    * If key(s) are matched and the key is None, the key is cleared
    * If key(s) aren't matched, group or Document is added
    """
    # If update is actually a list of state updates, run them one by one
    if isinstance(update, list):
        reduced = reduce(lambda current, update: document_reducer(current, update), update, current)
        return reduced

    # If state is empty, return update
    if current is None:
        return update

    # Copy current
    reduced = {k: v.copy() for k, v in current.items()}

    # Update with update
    for group_key, group in update.items():
        # If group is None, remove from output if a group key is matched
        if group is None:
            reduced.pop(group_key, None)
            continue

        # If group key isn't matched, add it
        if group_key not in reduced:
            reduced[group_key] = group

        for document_key, document in group.items():
            if document is None:
                # If Document is None, remove from output if a group and document key is matched
                reduced[group_key].pop(document_key, None)
            else:
                # Otherwise, update or add the value
                reduced[group_key][document_key] = document

        # Remove group_key from output if it becomes empty after updates
        if not reduced[group_key]:
            del reduced[group_key]

    return reduced


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
    def input_tokens(self):
        tokens_by_model = dict()
        for call_metadata in self.llm_calls:
            tokens_by_model[call_metadata.llm_model_name] = (
                tokens_by_model.get(call_metadata.llm_model_name, 0) + call_metadata.input_tokens
            )
        return tokens_by_model

    @property
    def output_tokens(self):
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
        llm_calls=sorted(list(set(current.llm_calls) | set(update.llm_calls)), key=lambda c: c.timestamp),
        selected_files_total_tokens=update.selected_files_total_tokens or current.selected_files_total_tokens,
        number_of_selected_files=update.number_of_selected_files or current.number_of_selected_files,
    )


class ToolStateEntry(TypedDict):
    """Represents a single tool call in the ToolState."""

    tool: ToolCall
    called: bool


class ToolState(dict[str, ToolStateEntry]):
    """Represents the state of multiple tools."""


def tool_calls_reducer(current: ToolState, update: ToolState | None) -> ToolState:
    """Handles updates to the tool state.

    * If a new key is added, adds it to the state.
    * If an existing key is None'd, removes it
    * If update is None, clears all tool calls
    """
    if not update:
        return {}

    # If update is actually a list of state updates, run them one by one
    if isinstance(update, list):
        reduced = reduce(lambda current, update: tool_calls_reducer(current, update), update, current)
        return reduced

    reduced = current.copy()

    for key, value in update.items():
        if value is None:
            reduced.pop(key, None)
        else:
            reduced[key] = value

    return reduced


class RedboxState(TypedDict):
    request: Required[RedboxQuery]
    documents: Annotated[NotRequired[DocumentState], document_reducer]
    text: NotRequired[str | None]
    route_name: NotRequired[str | None]
    tool_calls: Annotated[NotRequired[ToolState], tool_calls_reducer]
    metadata: Annotated[NotRequired[RequestMetadata], metadata_reducer]
    steps_left: RemainingSteps
    citations: NotRequired[list[Citation] | None]
    # steps_left: Annotated[NotRequired[int], RemainingStepsManager]


class PromptSet(StrEnum):
    Chat = "chat"
    ChatwithDocs = "chat_with_docs"
    ChatwithDocsMapReduce = "chat_with_docs_map_reduce"
    Search = "search"
    SearchAgentic = "search_agentic"
    GiveUpAgentic = "give_up_agentic"
    SelfRoute = "self_route"
    CondenseQuestion = "condense_question"


def get_prompts(state: RedboxState, prompt_set: PromptSet) -> tuple[str, str]:
    if prompt_set == PromptSet.Chat:
        system_prompt = state["request"].ai_settings.chat_system_prompt
        question_prompt = state["request"].ai_settings.chat_question_prompt
    elif prompt_set == PromptSet.ChatwithDocs:
        system_prompt = state["request"].ai_settings.chat_with_docs_system_prompt
        question_prompt = state["request"].ai_settings.chat_with_docs_question_prompt
    elif prompt_set == PromptSet.ChatwithDocsMapReduce:
        system_prompt = state["request"].ai_settings.chat_map_system_prompt
        question_prompt = state["request"].ai_settings.chat_map_question_prompt
    elif prompt_set == PromptSet.Search:
        system_prompt = state["request"].ai_settings.retrieval_system_prompt
        question_prompt = state["request"].ai_settings.retrieval_question_prompt
    elif prompt_set == PromptSet.SearchAgentic:
        system_prompt = state["request"].ai_settings.agentic_retrieval_system_prompt
        question_prompt = state["request"].ai_settings.agentic_retrieval_question_prompt
    elif prompt_set == PromptSet.GiveUpAgentic:
        system_prompt = state["request"].ai_settings.agentic_give_up_system_prompt
        question_prompt = state["request"].ai_settings.agentic_give_up_question_prompt
    elif prompt_set == PromptSet.SelfRoute:
        system_prompt = state["request"].ai_settings.self_route_system_prompt
        question_prompt = state["request"].ai_settings.retrieval_question_prompt
    elif prompt_set == PromptSet.CondenseQuestion:
        system_prompt = state["request"].ai_settings.condense_system_prompt
        question_prompt = state["request"].ai_settings.condense_question_prompt
    return (system_prompt, question_prompt)


def is_dict_type[T](annotated_type: T) -> bool:
    """Unwraps an annotated type to work out if it's a subclass of dict."""
    if get_origin(annotated_type) is Annotated:
        base_type = get_args(annotated_type)[0]
    else:
        base_type = annotated_type

    if get_origin(base_type) in {Required, NotRequired}:
        base_type = get_args(base_type)[0]

    return issubclass(base_type, dict)


def dict_reducer(current: dict, update: dict) -> dict:
    """
    Recursively merge two dictionaries:

    * If update has None for a key, current's key will be replaced with None.
    * If both values are dictionaries, they will be merged recursively.
    * Otherwise, the value in update will replace the value in current.
    """
    merged = current.copy()

    for key, new_value in update.items():
        if new_value is None:
            merged[key] = None
        elif isinstance(new_value, dict) and isinstance(merged.get(key), dict):
            merged[key] = dict_reducer(merged[key], new_value)
        else:
            merged[key] = new_value

    return merged


def merge_redbox_state_updates(current: RedboxState, update: RedboxState) -> RedboxState:
    """
    Merge RedboxStates to the following rules, intended for use on state updates.

    * Unannotated items are overwritten but never with None
    * Annotated items apply their reducer function
    * UNLESS they're a dictionary, in which case we use dict_reducer to preserve Nones
    """
    merged_state = current.copy()

    all_keys = set(current.keys()).union(set(update.keys()))

    for update_key in all_keys:
        current_value = current.get(update_key, None)
        update_value = update.get(update_key, None)

        annotation = RedboxState.__annotations__.get(update_key, None)

        if get_origin(annotation) is Annotated:
            if is_dict_type(annotation):
                # If it's annotated and a subclass of dict, apply a custom reducer function
                merged_state[update_key] = dict_reducer(current=current_value or {}, update=update_value or {})
            else:
                # If it's annotated and not a dict, apply its reducer function
                _, reducer_func = get_args(annotation)
                merged_state[update_key] = reducer_func(current_value, update_value)
        else:
            # If not annotated, replace but don't overwrite an existing value with None
            if update_value is not None:
                merged_state[update_key] = update_value
            else:
                merged_state[update_key] = current_value

    return merged_state
