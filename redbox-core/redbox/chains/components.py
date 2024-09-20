import logging
import os
from functools import cache

import tiktoken
from langchain_aws import ChatBedrock
from langchain_community.chat_models import ChatLiteLLM
from langchain_community.embeddings import BedrockEmbeddings
from langchain_core.embeddings import Embeddings, FakeEmbeddings
from langchain_core.utils import convert_to_secret_str
from langchain_elasticsearch import ElasticsearchRetriever
from langchain_openai import AzureChatOpenAI, ChatOpenAI
from langchain_openai.embeddings import AzureOpenAIEmbeddings, OpenAIEmbeddings
from redbox.api.callbacks import LoggerCallbackHandler
from redbox.models.chain import AISettings
from redbox.models.settings import Settings
from redbox.retriever import (
    AllElasticsearchRetriever,
    ParameterisedElasticsearchRetriever,
)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


def get_chat_llm(env: Settings, ai_settings: AISettings):
    chat_model = None
    if ai_settings.chat_backend == "openai":
        logger_callback = LoggerCallbackHandler(logger=log)
        chat_model = ChatOpenAI(
            streaming=True,
            callbacks=[logger_callback],
            model=env.openai_model,
            max_tokens=env.llm_max_tokens,
        )

    elif ai_settings.chat_backend == "gpt-35-turbo-16k":
        chat_model = AzureChatOpenAI(
            api_key=convert_to_secret_str(env.azure_openai_api_key_35t),
            azure_endpoint=env.azure_openai_endpoint_35t,
            model=ai_settings.chat_backend,
            api_version=env.openai_api_version_35t,
        )
        if env.azure_openai_fallback_endpoint_35t:
            chat_model.max_retries = 0
            chat_model = chat_model.with_fallbacks(
                [
                    AzureChatOpenAI(
                        api_key=convert_to_secret_str(
                            env.azure_openai_fallback_api_key_35t
                        ),
                        azure_endpoint=env.azure_openai_fallback_endpoint_35t,
                        model=ai_settings.chat_backend,
                        api_version=env.openai_api_version_35t,
                    )
                ]
            )
    elif ai_settings.chat_backend == "gpt-4-turbo-2024-04-09":
        chat_model = AzureChatOpenAI(
            api_key=convert_to_secret_str(env.azure_openai_api_key_4t),
            azure_endpoint=env.azure_openai_endpoint_4t,
            model=ai_settings.chat_backend,
            api_version=env.openai_api_version_4t,
        )
        if env.azure_openai_fallback_endpoint_4t:
            chat_model.max_retries = 0
            chat_model = chat_model.with_fallbacks(
                [
                    AzureChatOpenAI(
                        api_key=convert_to_secret_str(
                            env.azure_openai_fallback_api_key_4t
                        ),
                        azure_endpoint=env.azure_openai_fallback_endpoint_4t,
                        model=ai_settings.chat_backend,
                        api_version=env.openai_api_version_4t,
                    )
                ]
            )
    elif ai_settings.chat_backend == "gpt-4o":
        chat_model = AzureChatOpenAI(
            api_key=convert_to_secret_str(env.azure_openai_api_key_4o),
            azure_endpoint=env.azure_openai_endpoint_4o,
            model=ai_settings.chat_backend,
            api_version=env.openai_api_version_4o,
        )
        if env.azure_openai_fallback_endpoint_4o:
            chat_model.max_retries = 0
            chat_model = chat_model.with_fallbacks(
                [
                    AzureChatOpenAI(
                        api_key=convert_to_secret_str(
                            env.azure_openai_fallback_api_key_4o
                        ),
                        azure_endpoint=env.azure_openai_fallback_endpoint_4o,
                        model=ai_settings.chat_backend,
                        api_version=env.openai_api_version_4o,
                    )
                ]
            )
    elif ai_settings.chat_backend in (
        "anthropic.claude-3-sonnet-20240229-v1:0",
        "anthropic.claude-3-haiku-20240307-v1:0",
    ):
        chat_model = ChatBedrock(model_id=ai_settings.chat_backend)

    if chat_model is None:
        raise Exception("%s not recognised", ai_settings.chat_backend)
    else:
        return chat_model


@cache
def get_tokeniser() -> tiktoken.Encoding:
    return tiktoken.get_encoding("cl100k_base")


def get_azure_embeddings(env: Settings):
    return AzureOpenAIEmbeddings(
        api_key=convert_to_secret_str(env.embedding_openai_api_key),
        azure_endpoint=env.embedding_azure_openai_endpoint,
        api_version=env.azure_api_version_embeddings,
        model=env.embedding_backend,
        max_retries=env.embedding_max_retries,
        retry_min_seconds=env.embedding_retry_min_seconds,
        retry_max_seconds=env.embedding_retry_max_seconds,
    )


def get_openai_embeddings(env: Settings):
    # os.environ["OPENAI_API_KEY"] = env.embedding_openai_api_key
    # os.environ["OPENAI_ENDPOINT"] = env.embedding_openai_base_url
    return OpenAIEmbeddings(
        api_key=convert_to_secret_str(env.embedding_openai_api_key),
        base_url=env.embedding_openai_base_url,
        model=env.embedding_backend,
        chunk_size=env.embedding_max_batch_size,
    )


def get_aws_embeddings(env: Settings):
    return BedrockEmbeddings(region_name=env.aws_region, model_id=env.embedding_backend)


def get_embeddings(env: Settings) -> Embeddings:
    if env.embedding_backend == "text-embedding-3-large":
        return get_azure_embeddings(env)
    if env.embedding_backend == "text-embedding-ada-002":
        return get_openai_embeddings(env)
    if env.embedding_backend == "fake":
        return FakeEmbeddings(size=3072)
    if env.embedding_backend == "amazon.titan-embed-text-v2:0":
        return get_aws_embeddings(env)
    raise Exception("No configured embedding model")


def get_all_chunks_retriever(env: Settings) -> ElasticsearchRetriever:
    return AllElasticsearchRetriever(
        es_client=env.elasticsearch_client(),
        index_name=f"{env.elastic_root_index}-chunk",
    )


def get_parameterised_retriever(env: Settings, embeddings: Embeddings | None = None):
    """Creates an Elasticsearch retriever runnable.

    Runnable takes input of a dict keyed to question, file_uuids and user_uuid.

    Runnable returns a list of Chunks.
    """
    return ParameterisedElasticsearchRetriever(
        es_client=env.elasticsearch_client(),
        index_name=f"{env.elastic_root_index}-chunk",
        embedding_model=embeddings or get_embeddings(env),
        embedding_field_name=env.embedding_document_field_name,
    )
