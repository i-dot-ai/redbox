import os
from functools import cache
from langchain_elasticsearch import ElasticsearchRetriever
from langchain_core.embeddings import Embeddings, FakeEmbeddings
from langchain_openai import AzureChatOpenAI
from langchain_openai.embeddings import AzureOpenAIEmbeddings, OpenAIEmbeddings
from langchain_core.utils import convert_to_secret_str
import tiktoken

from redbox.models.chain import AISettings
from redbox.models.settings import Settings
from redbox.retriever import AllElasticsearchRetriever, ParameterisedElasticsearchRetriever


def get_chat_llm(env: Settings, ai_settings: AISettings):
    if ai_settings.chat_backend == "azure/gpt-35-turbo-16k":
        os.environ["AZURE_OPENAI_ENDPOINT"] = env.azure_openai_endpoint_35t
        os.environ["AZURE_OPENAI_API_KEY"] = env.azure_openai_api_key_35t
        return AzureChatOpenAI(
            api_key=convert_to_secret_str(env.azure_openai_api_key_35t),
            azure_endpoint=env.azure_openai_endpoint_35t,
            model=ai_settings.chat_backend,
            api_version=env.openai_api_version_35t,
        )
    if ai_settings.chat_backend == "azure/gpt-4":
        os.environ["AZURE_OPENAI_ENDPOINT"] = env.azure_openai_endpoint_4t
        os.environ["AZURE_OPENAI_API_KEY"] = env.azure_openai_api_key_4t
        return AzureChatOpenAI(
            api_key=convert_to_secret_str(env.azure_openai_api_key_4t),
            azure_endpoint=env.azure_openai_endpoint_4t,
            model=ai_settings.chat_backend,
            api_version=env.openai_api_version_4t,
        )
    if ai_settings.chat_backend == "azure/gpt-4o":
        os.environ["AZURE_OPENAI_ENDPOINT"] = env.azure_openai_endpoint_4o
        os.environ["AZURE_OPENAI_API_KEY"] = env.azure_openai_api_key_4o
        return AzureChatOpenAI(
            api_key=convert_to_secret_str(env.azure_openai_api_key_4o),
            azure_endpoint=env.azure_openai_endpoint_4o,
            model=ai_settings.chat_backend,
            api_version=env.openai_api_version_4o,
        )
    raise Exception(f"{ai_settings.chat_backend} not recognised")


@cache
def get_tokeniser() -> tiktoken.Encoding:
    return tiktoken.get_encoding("cl100k_base")


def get_azure_embeddings(env: Settings):
    return AzureOpenAIEmbeddings(
        api_key=convert_to_secret_str(env.azure_openai_api_key),
        azure_endpoint=env.embedding_azure_openai_endpoint,
        api_version=env.azure_api_version_embeddings,
        model=env.azure_embedding_model,
        max_retries=env.embedding_max_retries,
        retry_min_seconds=env.embedding_retry_min_seconds,
        retry_max_seconds=env.embedding_retry_max_seconds,
    )


def get_openai_embeddings(env: Settings):
    return OpenAIEmbeddings(
        api_key=convert_to_secret_str(env.embedding_openai_api_key),
        base_url=env.embedding_openai_base_url,
        model=env.embedding_openai_model,
        chunk_size=env.embedding_max_batch_size,
    )


def get_embeddings(env: Settings) -> Embeddings:
    if env.embedding_backend == "azure":
        return get_azure_embeddings(env)
    elif env.embedding_backend == "openai":
        return get_openai_embeddings(env)
    elif env.embedding_backend == "fake":
        return FakeEmbeddings(size=3072)  # TODO
    else:
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
