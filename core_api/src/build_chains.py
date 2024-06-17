import logging
from http import HTTPStatus
from http.client import HTTPException
from operator import itemgetter
from typing import Any

import numpy as np
from langchain.schema import StrOutputParser
from langchain_community.chat_models import ChatLiteLLM
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableLambda, RunnablePassthrough, chain
from langchain_core.vectorstores import VectorStoreRetriever

from core_api.src.format import format_chunks, get_file_chunked_to_tokens
from core_api.src.runnables import make_chat_prompt_from_messages_runnable
from redbox.models import ChatRequest, Chunk, Settings
from redbox.storage import ElasticsearchStorageHandler

# === Logging ===

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()

env = Settings()

# Define the system prompt for summarization
summarisation_prompt = (
    "You are an AI assistant tasked with summarizing documents. "
    "Your goal is to extract the most important information and present it in "
    "a concise and coherent manner. Please follow these guidelines while summarizing: \n"
    "1) Identify and highlight key points,\n"
    "2) Avoid repetition,\n"
    "3) Ensure the summary is easy to understand,\n"
    "4) Maintain the original context and meaning.\n"
)


def build_vanilla_chain(
    chat_request: ChatRequest,
    **kwargs,  # noqa: ARG001
) -> ChatPromptTemplate:
    """Get a LLM response to a question history"""

    if len(chat_request.message_history) < 2:  # noqa: PLR2004
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            detail="Chat history should include both system and user prompts",
        )

    if chat_request.message_history[0].role != "system":
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            detail="The first entry in the chat history should be a system prompt",
        )

    if chat_request.message_history[-1].role != "user":
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            detail="The final entry in the chat history should be a user question",
        )

    return ChatPromptTemplate.from_messages((msg.role, msg.text) for msg in chat_request.message_history)


def build_retrieval_chain(
    llm: ChatLiteLLM,
    retriever: VectorStoreRetriever,
    system_prompt: str,
    question_prompt: str,
    **kwargs,  # noqa: ARG001
) -> tuple[Runnable, dict[str, Any]]:
    return (
        RunnablePassthrough.assign(documents=retriever)
        | RunnablePassthrough.assign(
            formatted_documents=(RunnablePassthrough() | itemgetter("documents") | format_chunks)
        )
        | {
            "response": make_chat_prompt_from_messages_runnable(system_prompt, question_prompt)
            | llm
            | StrOutputParser(),
            "source_documents": itemgetter("documents"),
        }
    )


def build_summary_chain(
    llm: ChatLiteLLM,
    storage_handler: ElasticsearchStorageHandler,
    system_prompt: str,
    question_prompt: str,
    **kwargs,  # noqa: ARG001
) -> tuple[Runnable, dict[str, Any]]:
    @chain
    def make_document_context(input_dict):
        documents: list[Chunk] = []
        for selected_file in input_dict["file_uuids"]:
            chunks = get_file_chunked_to_tokens(
                file_uuid=selected_file,
                user_uuid=input_dict["user_uuid"],
                storage_handler=storage_handler,
            )
            documents += chunks

        # right now, can only handle a single document so we manually truncate
        max_tokens = 20_000  # parameterise later
        doc_token_sum = np.cumsum([doc.token_count for doc in documents])
        doc_token_sum_limit_index = len([i for i in doc_token_sum if i < max_tokens])

        documents_trunc = documents[:doc_token_sum_limit_index]
        if len(documents) < doc_token_sum_limit_index:
            log.info("Documents were longer than 20k tokens. Truncating to the first 20k.")
        return documents_trunc

    return (
        RunnablePassthrough.assign(documents=(make_document_context | RunnableLambda(format_chunks)))
        | make_chat_prompt_from_messages_runnable(system_prompt, question_prompt)
        | llm
        | {"response": StrOutputParser()}
    )


def build_static_response_chain(prompt_template):
    return RunnablePassthrough.assign(
        response=(ChatPromptTemplate.from_template(prompt_template) | RunnableLambda(lambda p: p.messages[0].content)),
        source_documents=RunnableLambda(lambda _: []),
    )
