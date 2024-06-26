import logging
from operator import itemgetter
from typing import Annotated

import numpy as np
from fastapi import Depends
from langchain.prompts import PromptTemplate
from langchain.schema import StrOutputParser
from langchain_community.chat_models import ChatLiteLLM
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import (
    Runnable,
    RunnableLambda,
    RunnablePassthrough,
    chain,
)
from langchain_core.runnables.config import RunnableConfig
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_core.retrievers import BaseRetriever

from core_api.src import dependencies
from core_api.src.format import format_chunks, format_documents
from core_api.src.runnables import make_chat_prompt_from_messages_runnable, resize_documents
from redbox.models import ChatRoute, Settings
from redbox.storage import ElasticsearchStorageHandler

# === Logging ===

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


def build_vanilla_chain(
    llm: Annotated[ChatLiteLLM, Depends(dependencies.get_llm)],
    env: Annotated[Settings, Depends(dependencies.get_env)],
) -> Runnable:
    return (
        make_chat_prompt_from_messages_runnable(env.ai.vanilla_system_prompt, env.ai.vanilla_question_prompt)
        | llm
        | {
            "response": StrOutputParser(),
            "route_name": RunnableLambda(lambda _: ChatRoute.vanilla.value),
        }
    )


def build_retrieval_chain(
    llm: Annotated[ChatLiteLLM, Depends(dependencies.get_llm)],
    retriever: Annotated[VectorStoreRetriever, Depends(dependencies.get_parameterised_retriever)],
    env: Annotated[Settings, Depends(dependencies.get_env)],
) -> Runnable:
    return (
        RunnablePassthrough.assign(documents=retriever)
        | RunnablePassthrough.assign(
            formatted_documents=(RunnablePassthrough() | itemgetter("documents") | format_documents)
        )
        | {
            "response": make_chat_prompt_from_messages_runnable(
                env.ai.retrieval_system_prompt, env.ai.retrieval_question_prompt
            )
            | llm
            | StrOutputParser(),
            "source_documents": itemgetter("documents"),
            "route_name": RunnableLambda(lambda _: ChatRoute.search.value),
        }
    )


def build_summary_chain(
    llm: Annotated[ChatLiteLLM, Depends(dependencies.get_llm)],
    all_chunks_retriever: Annotated[BaseRetriever, Depends(dependencies.get_all_chunks_retriever)],
    env: Annotated[Settings, Depends(dependencies.get_env)],
) -> Runnable:
    def make_document_context(input_dict):
        documents = (
            all_chunks_retriever
            |
            {
            str(file_uuid): resize_documents(env.ai.rag_desired_chunk_size)
            for file_uuid in input_dict['file_uuids']
            }
            | RunnableLambda(lambda f: [chunk for chunk_lists in f.values() for chunk in chunk_lists])
        ).invoke(input_dict)

        # right now, can only handle a single document so we manually truncate
        max_tokens = (env.ai.summarisation_chunk_max_tokens,)
        doc_token_sum = np.cumsum([doc.metadata['token_count'] for doc in documents])
        doc_token_sum_limit_index = len([i for i in doc_token_sum if i < max_tokens])

        documents_trunc = documents[:doc_token_sum_limit_index]
        if len(documents) < doc_token_sum_limit_index:
            log.info("Documents were longer than 20k tokens. Truncating to the first 20k.")
        return documents_trunc

    return (
        RunnablePassthrough.assign(documents=(make_document_context | RunnableLambda(format_documents)))
        | make_chat_prompt_from_messages_runnable(
            env.ai.summarisation_system_prompt, env.ai.summarisation_question_prompt
        )
        | llm
        | {
            "response": StrOutputParser(),
            "route_name": RunnableLambda(lambda _: ChatRoute.summarise.value),
        }
    )


def build_map_reduce_summary_chain(
    llm: Annotated[ChatLiteLLM, Depends(dependencies.get_llm)],
    all_chunks_retriever: Annotated[BaseRetriever, Depends(dependencies.get_all_chunks_retriever)],
    env: Annotated[Settings, Depends(dependencies.get_env)],
) -> Runnable:
    def make_document_context(input_dict: dict):

        return (
            all_chunks_retriever
            |
            {
            file_uuid: resize_documents(env.ai.rag_desired_chunk_size)
            for file_uuid in input_dict['file_uuids']
            }
            | RunnableLambda(lambda f: [chunk.page_content for chunk_lists in f.values() for chunk in chunk_lists])
        ).invoke(input_dict)

    @chain
    def map_operation(input_dict):
        system_map_prompt = env.ai.map_system_prompt
        prompt_template = PromptTemplate.from_template(env.ai.map_question_prompt)

        formatted_map_question_prompt = prompt_template.format(question=input_dict["question"])

        map_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_map_prompt),
                ("human", formatted_map_question_prompt + env.ai.map_document_prompt),
            ]
        )

        documents = [chunk.text for chunk in input_dict["documents"]]

        map_summaries = (map_prompt | llm | StrOutputParser()).batch(
            documents,
            config=RunnableConfig(max_concurrency=env.ai.summarisation_max_concurrency),
        )

        summaries = " ; ".join(map_summaries)
        input_dict["summaries"] = summaries
        return input_dict

    return (
        RunnablePassthrough.assign(documents=make_document_context)
        | map_operation
        | make_chat_prompt_from_messages_runnable(env.ai.reduce_system_prompt, env.ai.reduce_question_prompt)
        | llm
        | {
            "response": StrOutputParser(),
            "route_name": RunnableLambda(lambda _: ChatRoute.summarise.value),
        }
    )


def build_static_response_chain(prompt_template, route_name) -> Runnable:
    return RunnablePassthrough.assign(
        response=(ChatPromptTemplate.from_template(prompt_template) | RunnableLambda(lambda p: p.messages[0].content)),
        source_documents=RunnableLambda(lambda _: []),
        route_name=RunnableLambda(lambda _: route_name.value),
    )
