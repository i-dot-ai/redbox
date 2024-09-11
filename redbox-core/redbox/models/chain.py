"""
There is some repeated definition and non-pydantic style code in here.
These classes are pydantic v1 which is compatible with langchain tools classes, we need
to provide a pydantic v1 definition to work with these. As these models are mostly
used in conjunction with langchain this is the tidiest boxing of pydantic v1 we can do
"""

from typing import TypedDict, Literal, Annotated, Required, NotRequired
from uuid import UUID
from functools import reduce
from enum import StrEnum

from pydantic import BaseModel, Field
from langchain_core.documents import Document


class ChainChatMessage(TypedDict):
    role: Literal["user", "ai", "system"]
    text: str


CHAT_SYSTEM_PROMPT = (
    "You are an AI assistant called Redbox tasked with answering questions and providing information objectively."
)

CHAT_WITH_DOCS_SYSTEM_PROMPT = "You are an AI assistant called Redbox tasked with answering questions on user provided documents and providing information objectively."

CHAT_WITH_DOCS_REDUCE_SYSTEM_PROMPT = (
    "You are an AI assistant tasked with answering questions on user provided documents. "
    "Your goal is to answer the user question based on list of summaries in a coherent manner."
    "Please follow these guidelines while answering the question: \n"
    "1) Identify and highlight key points,\n"
    "2) Avoid repetition,\n"
    "3) Ensure the answer is easy to understand,\n"
    "4) Maintain the original context and meaning.\n"
)

RETRIEVAL_SYSTEM_PROMPT = (
    "Given the following conversation and extracted parts of a long document and a question, create a final answer. \n"
    "If you don't know the answer, just say that you don't know. Don't try to make up an answer. "
    "If a user asks for a particular format to be returned, such as bullet points, then please use that format. "
    "If a user asks for bullet points you MUST give bullet points. "
    "If the user asks for a specific number or range of bullet points you MUST give that number of bullet points. \n"
    "Use **bold** to highlight the most question relevant parts in your response. "
    "If dealing dealing with lots of data return it in markdown table format. "
)

CHAT_MAP_SYSTEM_PROMPT = (
    "You are an AI assistant tasked with summarizing documents. "
    "Your goal is to extract the most important information and present it in "
    "a concise and coherent manner. Please follow these guidelines while summarizing: \n"
    "1) Identify and highlight key points,\n"
    "2) Avoid repetition,\n"
    "3) Ensure the summary is easy to understand,\n"
    "4) Maintain the original context and meaning.\n"
)

REDUCE_SYSTEM_PROMPT = (
    "You are an AI assistant tasked with summarizing documents. "
    "Your goal is to write a concise summary of list of summaries from a list of summaries in "
    "a concise and coherent manner. Please follow these guidelines while summarizing: \n"
    "1) Identify and highlight key points,\n"
    "2) Avoid repetition,\n"
    "3) Ensure the summary is easy to understand,\n"
    "4) Maintain the original context and meaning.\n"
)

CONDENSE_SYSTEM_PROMPT = (
    "Given the following conversation and a follow up question, generate a follow "
    "up question to be a standalone question. "
    "You are only allowed to generate one question in response. "
    "Include sources from the chat history in the standalone question created, "
    "when they are available. "
    "If you don't know the answer, just say that you don't know, "
    "don't try to make up an answer. \n"
)

CHAT_QUESTION_PROMPT = "{question}\n=========\n Response: "

CHAT_WITH_DOCS_QUESTION_PROMPT = "Question: {question}. \n\n Documents: \n\n {formatted_documents} \n\n Answer: "

RETRIEVAL_QUESTION_PROMPT = "{question} \n=========\n{formatted_documents}\n=========\nFINAL ANSWER: "

CHAT_MAP_QUESTION_PROMPT = "Question: {question}. \n Documents: \n {formatted_documents} \n\n Answer: "

CONDENSE_QUESTION_PROMPT = "{question}\n=========\n Standalone question: "


class AISettings(BaseModel):
    """prompts and other AI settings"""

    max_document_tokens: int = 1_000_000
    context_window_size: int = 128_000
    llm_max_tokens: int = 1024

    rag_k: int = 30
    rag_num_candidates: int = 10
    elbow_filter_enabled: bool = False
    chat_system_prompt: str = CHAT_SYSTEM_PROMPT
    chat_question_prompt: str = CHAT_QUESTION_PROMPT
    stuff_chunk_context_ratio: float = 0.75
    chat_with_docs_system_prompt: str = CHAT_WITH_DOCS_SYSTEM_PROMPT
    chat_with_docs_question_prompt: str = CHAT_WITH_DOCS_QUESTION_PROMPT
    chat_with_docs_reduce_system_prompt: str = CHAT_WITH_DOCS_REDUCE_SYSTEM_PROMPT
    retrieval_system_prompt: str = RETRIEVAL_SYSTEM_PROMPT
    retrieval_question_prompt: str = RETRIEVAL_QUESTION_PROMPT
    condense_system_prompt: str = CONDENSE_SYSTEM_PROMPT
    condense_question_prompt: str = CONDENSE_QUESTION_PROMPT
    map_max_concurrency: int = 128
    chat_map_system_prompt: str = CHAT_MAP_SYSTEM_PROMPT
    chat_map_question_prompt: str = CHAT_MAP_QUESTION_PROMPT
    reduce_system_prompt: str = REDUCE_SYSTEM_PROMPT

    match_boost: int = 1
    knn_boost: int = 1
    similarity_threshold: int = 0

    # this is also the azure_openai_model
    chat_backend: Literal[
        "gpt-35-turbo-16k",
        "gpt-4-turbo-2024-04-09",
        "gpt-4o",
        "anthropic.claude-3-sonnet-20240229-v1:0",
        "anthropic.claude-3-haiku-20240307-v1:0",
    ] = "gpt-4o"


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


class RequestMetadata(TypedDict):
    input_tokens: dict[str, int]
    output_tokens: dict[str, int]


def add_tokens_by_model(current: dict[str, int], update: dict[str, int]):
    result = current.copy()

    for key, value in update.items():
        result[key] = (result.get(key) or 0) + value

    return result


def metadata_reducer(current: RequestMetadata | None, update: RequestMetadata | list[RequestMetadata] | None):
    """Merges two metadata states."""
    # If update is actually a list of state updates, run them one by one
    if isinstance(update, list):
        reduced = reduce(lambda current, update: metadata_reducer(current, update), update, current)
        return reduced

    if current is None:
        return update
    if update is None:
        return current

    input_tokens = add_tokens_by_model(current.get("input_tokens") or {}, update.get("input_tokens") or {})
    output_tokens = add_tokens_by_model(current.get("output_tokens") or {}, update.get("output_tokens") or {})

    return RequestMetadata(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )


class RedboxState(TypedDict):
    request: Required[RedboxQuery]
    documents: Annotated[NotRequired[DocumentState], document_reducer]
    text: NotRequired[str | None]
    route_name: NotRequired[str | None]
    metadata: Annotated[NotRequired[dict], metadata_reducer]


class PromptSet(StrEnum):
    Chat = "chat"
    ChatwithDocs = "chat_with_docs"
    ChatwithDocsMapReduce = "chat_with_docs_map_reduce"
    Search = "search"
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
    elif prompt_set == PromptSet.CondenseQuestion:
        system_prompt = state["request"].ai_settings.condense_system_prompt
        question_prompt = state["request"].ai_settings.condense_question_prompt
    return (system_prompt, question_prompt)
