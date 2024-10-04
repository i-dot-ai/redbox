import os
from functools import cache
from langchain_elasticsearch import ElasticsearchRetriever
from langchain_core.embeddings import Embeddings, FakeEmbeddings
from langchain_openai import AzureChatOpenAI
from langchain_openai.embeddings import AzureOpenAIEmbeddings, OpenAIEmbeddings
from langchain_core.utils import convert_to_secret_str
import tiktoken

from redbox.models.chain import AISettings
from redbox.models.settings import Settings, GPTModels
from redbox.retriever import AllElasticsearchRetriever, ParameterisedElasticsearchRetriever, MetadataRetriever
from langchain_aws import ChatBedrock
from langchain_community.embeddings import BedrockEmbeddings


def get_chat_llm(ai_settings: AISettings):
    if ai_settings.chat_backend in ("gpt-35-turbo-16k", "gpt-4-turbo-2024-04-09", "gpt-4o"):
        openai_api_models = GPTModels()
        azure_openai_api = openai_api_models[ai_settings.chat_backend]

        chat_model = AzureChatOpenAI(
            api_key=convert_to_secret_str(azure_openai_api.api_key),
            azure_endpoint=azure_openai_api.endpoint,
            model=azure_openai_api.id,
            api_version=azure_openai_api.api_version,
        )
        if azure_openai_api.fallback_endpoint:
            chat_model.max_retries = 0
            chat_model = chat_model.with_fallbacks(
                [
                    AzureChatOpenAI(
                        api_key=convert_to_secret_str(azure_openai_api.fallback_api_key),
                        azure_endpoint=azure_openai_api.fallback_endpoint,
                        model=azure_openai_api.id,
                        api_version=azure_openai_api.version,
                    )
                ]
            )
        return chat_model

    elif ai_settings.chat_backend in (
        "anthropic.claude-3-sonnet-20240229-v1:0",
        "anthropic.claude-3-haiku-20240307-v1:0",
    ):
        return ChatBedrock(model_id=ai_settings.chat_backend)

    raise Exception("%s not recognised", ai_settings.chat_backend)


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
    os.environ["OPENAI_API_KEY"] = env.embedding_openai_api_key
    os.environ["OPENAI_ENDPOINT"] = env.embedding_openai_base_url
    return OpenAIEmbeddings(
        api_key=convert_to_secret_str(env.embedding_openai_api_key),
        base_url=env.embedding_openai_base_url,
        model=env.embedding_model,
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


def get_metadata_retriever(env: Settings):
    return MetadataRetriever(
        es_client=env.elasticsearch_client(),
        index_name=f"{env.elastic_root_index}-chunk",
    )
