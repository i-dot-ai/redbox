import logging
import os
from functools import lru_cache
from typing import Annotated

import tiktoken
from fastapi import Depends
from langchain_community.chat_models import ChatLiteLLM
from langchain_core.embeddings import Embeddings
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import ConfigurableField
from redbox.api.callbacks import LoggerCallbackHandler
from redbox.embeddings import get_embeddings
from redbox.models import Settings
from redbox.retriever import (
    AllElasticsearchRetriever,
    ParameterisedElasticsearchRetriever,
)
from redbox.storage import ElasticsearchStorageHandler

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


@lru_cache(1)
def get_env() -> Settings:
    return Settings()


@lru_cache(1)
def get_embedding_model(env: Annotated[Settings, Depends(get_env)]) -> Embeddings:
    return get_embeddings(env)


@lru_cache(1)
def get_parameterised_retriever(
    env: Annotated[Settings, Depends(get_env)],
) -> BaseRetriever:
    """Creates an Elasticsearch retriever runnable.

    Runnable takes input of a dict keyed to question, file_uuids and user_uuid.

    Runnable returns a list of Chunks.
    """
    default_params = {
        "size": env.ai.rag_k,
        "num_candidates": env.ai.rag_num_candidates,
        "match_boost": 1,
        "knn_boost": 1,
        "similarity_threshold": 0,
    }
    return ParameterisedElasticsearchRetriever(
        es_client=env.elasticsearch_client(),
        index_name=f"{env.elastic_root_index}-chunk",
        params=default_params,
        embedding_model=get_embedding_model(env),
        embedding_field_name=env.embedding_document_field_name,
    ).configurable_fields(
        params=ConfigurableField(
            id="params",
            name="Retriever parameters",
            description="A dictionary of parameters to use for the retriever.",
        )
    )


@lru_cache(1)
def get_all_chunks_retriever(env: Annotated[Settings, Depends(get_env)]):
    return AllElasticsearchRetriever(
        es_client=env.elasticsearch_client(),
        index_name=f"{env.elastic_root_index}-chunk",
    )


@lru_cache(1)
def get_llm(env: Annotated[Settings, Depends(get_env)]) -> ChatLiteLLM:
    logger_callback = LoggerCallbackHandler(logger=log)

    # Create the appropriate LLM, either openai, Azure, anthropic or bedrock
    if env.chat_backend == "openai":
        log.info("Creating OpenAI LLM Client")
        llm = ChatLiteLLM(
            streaming=True,
            openai_key=env.openai_api_key,
            callbacks=[logger_callback],
            model=env.openai_model,
            max_tokens=env.llm_max_tokens,
        )
    elif env.chat_backend == "azure":
        log.info("Creating Azure LLM Client")
        log.info("api_base: %s", env.azure_openai_endpoint)
        log.info("api_version: %s", env.openai_api_version)
        log.info("llm_max_tokens: %i", env.llm_max_tokens)

        # this nasty hack is required because, contrary to the docs:
        # using the api_version argument is not sufficient, and we need
        # to use the `OPENAI_API_VERSION` environment variable
        os.environ["AZURE_API_VERSION"] = env.openai_api_version
        os.environ["AZURE_OPENAI_API_KEY"] = env.azure_openai_api_key

        llm = ChatLiteLLM(
            model=env.azure_openai_model,
            azure_api_key=env.azure_openai_api_key,
            streaming=True,
            api_base=env.azure_openai_endpoint,
            max_tokens=env.llm_max_tokens,
            callbacks=[logger_callback],
        )
    else:
        msg = "Unknown LLM model specified or missing"
        log.exception(msg)
        raise ValueError(msg)
    return llm


@lru_cache(1)
def get_tokeniser() -> tiktoken.Encoding:
    return tiktoken.get_encoding("cl100k_base")
