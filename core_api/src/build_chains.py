import logging
from http import HTTPStatus
from http.client import HTTPException
from operator import itemgetter
from typing import Annotated, Any

import numpy as np
from fastapi import Depends
from langchain.globals import set_debug
from langchain.schema import StrOutputParser
from langchain_community.chat_models import ChatLiteLLM
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import (
    Runnable,
    RunnableLambda,
    RunnablePassthrough,
    chain,
)
from langchain_core.vectorstores import VectorStoreRetriever

from core_api.src import dependencies
from core_api.src.format import format_chunks, get_file_chunked_to_tokens
from core_api.src.runnables import make_chat_prompt_from_messages_runnable
from redbox.models import ChatRequest, Chunk, Settings
from redbox.storage import ElasticsearchStorageHandler

# === Logging ===

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


def build_vanilla_chain(
    chat_request: ChatRequest,
    **kwargs,  # noqa: ARG001
) -> Runnable:
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

    return ChatPromptTemplate.from_messages(
        (msg.role, msg.text) for msg in chat_request.message_history
    )


def build_retrieval_chain(
    llm: Annotated[ChatLiteLLM, Depends(dependencies.get_llm)],
    retriever: Annotated[VectorStoreRetriever, Depends(dependencies.get_es_retriever)],
    env: Annotated[Settings, Depends(dependencies.get_env)],
) -> Runnable:
    return (
        RunnablePassthrough.assign(documents=retriever)
        | RunnablePassthrough.assign(
            formatted_documents=(
                RunnablePassthrough() | itemgetter("documents") | format_chunks
            )
        )
        | {
            "response": make_chat_prompt_from_messages_runnable(
                env.ai.retrieval_system_prompt, env.ai.retrieval_question_prompt
            )
            | llm
            | StrOutputParser(),
            "source_documents": itemgetter("documents"),
        }
    )


def build_summary_chain(
    llm: Annotated[ChatLiteLLM, Depends(dependencies.get_llm)],
    storage_handler: Annotated[
        ElasticsearchStorageHandler, Depends(dependencies.get_storage_handler)
    ],
    env: Annotated[Settings, Depends(dependencies.get_env)],
) -> Runnable:
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
            log.info(
                "Documents were longer than 20k tokens. Truncating to the first 20k."
            )
        return documents_trunc

    return (
        RunnablePassthrough.assign(
            documents=(make_document_context | RunnableLambda(format_chunks))
        )
        | make_chat_prompt_from_messages_runnable(
            env.ai.summarisation_system_prompt, env.ai.summarisation_question_prompt
        )
        | llm
        | {"response": StrOutputParser()}
    )


def prepare_list_of_docs(
    llm: Annotated[ChatLiteLLM, Depends(dependencies.get_llm)],
    storage_handler: Annotated[
        ElasticsearchStorageHandler, Depends(dependencies.get_storage_handler)
    ],
    env: Annotated[Settings, Depends(dependencies.get_env)],
) -> Runnable:
    def make_document_context(input_dict: dict):
        documents: list[str] = []
        for selected_file in input_dict["file_uuids"]:
            chunks = get_file_chunked_to_tokens(
                file_uuid=selected_file,
                user_uuid=input_dict["user_uuid"],
                storage_handler=storage_handler,
                max_tokens=20_000,
            )
            documents += [chunk.text for chunk in chunks]

        return documents

    return make_document_context


def build_map_reduce_summary_chain(
    llm: Annotated[ChatLiteLLM, Depends(dependencies.get_llm)],
    storage_handler: Annotated[
        ElasticsearchStorageHandler, Depends(dependencies.get_storage_handler)
    ],
    env: Annotated[Settings, Depends(dependencies.get_env)],
) -> Runnable:
    def make_document_context(input_dict: dict):
        documents: list[str] = []
        for selected_file in input_dict["file_uuids"]:
            chunks = get_file_chunked_to_tokens(
                file_uuid=selected_file,
                user_uuid=input_dict["user_uuid"],
                storage_handler=storage_handler,
                max_tokens=20_000,
            )
            documents += [chunk.text for chunk in chunks]

        return documents

    map_step = (
        RunnablePassthrough.assign(documents=make_document_context)
        | make_chat_prompt_from_messages_runnable(
            env.ai.map_system_prompt, env.ai.map_question_prompt
        )
        | llm
        | StrOutputParser()
    )

    # def map_operation(input_dict: dict):
    #     log.info(f"input_dict before map_step {input_dict}")
    #     return map_step.invoke(input_dict)
    def map_operation(input_dict: dict):
        # log.info(f"input_dict before map_step: {input_dict}")
        output = map_step.invoke(input_dict)

        # Add the output to the input_dict as a new key
        input_dict["documents"] = output

        log.info(f"input_dict after adding map_step_output: {input_dict}")
        return input_dict

    return (
        map_operation
        | make_chat_prompt_from_messages_runnable(
            env.ai.reduce_system_prompt, env.ai.reduce_question_prompt
        )
        | llm
        | {"response": StrOutputParser()}
    )


def build_static_response_chain(prompt_template) -> Runnable:
    return RunnablePassthrough.assign(
        response=(
            ChatPromptTemplate.from_template(prompt_template)
            | RunnableLambda(lambda p: p.messages[0].content)
        ),
        source_documents=RunnableLambda(lambda _: []),
    )
