import logging

import os
from functools import cache

import tiktoken

from dotenv import load_dotenv
from langchain_core.embeddings import Embeddings, FakeEmbeddings
from langchain_core.tools import StructuredTool
from langchain_core.runnables import Runnable
from langchain_core.utils import convert_to_secret_str
from langchain_elasticsearch import ElasticsearchRetriever
from langchain_openai.embeddings import AzureOpenAIEmbeddings, OpenAIEmbeddings


from redbox.chains.parser import StreamingJsonOutputParser
from redbox.models.settings import ChatLLMBackend, Settings
from redbox.retriever import AllElasticsearchRetriever, MetadataRetriever
from langchain_community.embeddings import BedrockEmbeddings
from langchain.chat_models import init_chat_model
from redbox.models.chain import StructuredResponseWithCitations


logger = logging.getLogger(__name__)
load_dotenv()


def get_chat_llm(model: ChatLLMBackend, tools: list[StructuredTool] | None = None):
    logger.debug("initialising model=%s model_provider=%s tools=%s", model.name, model.provider, tools)
    chat_model = init_chat_model(
        model=model.name,
        model_provider=model.provider,
        configurable_fields=["base_url"],
    )
    if tools:
        chat_model = chat_model.bind_tools(tools)
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
        index_name=env.elastic_chunk_alias,
    )


def get_metadata_retriever(env: Settings):
    return MetadataRetriever(
        es_client=env.elasticsearch_client(),
        index_name=env.elastic_chunk_alias,
    )


def get_structured_response_with_citations_parser() -> tuple[Runnable, str]:
    """
    Returns the output parser (as a runnable) for creating the StructuredResponseWithCitations object
    while streaming the answer tokens
    Also returns the format instructions for this structure for use in the prompt
    """
    # pydantic_parser = PydanticOutputParser(pydantic_object=StructuredResponseWithCitations)
    parser = StreamingJsonOutputParser(
        name_of_streamed_field="answer", pydantic_schema_object=StructuredResponseWithCitations
    )
    return (parser, parser.get_format_instructions())
