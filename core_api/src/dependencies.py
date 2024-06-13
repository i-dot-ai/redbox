import logging
import os
from typing import Annotated

from elasticsearch import Elasticsearch
from fastapi import Depends
from langchain_community.chat_models import ChatLiteLLM
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_core.embeddings import Embeddings
from langchain_elasticsearch import ApproxRetrievalStrategy, ElasticsearchStore

from redbox.model_db import MODEL_PATH
from redbox.models import Settings
from redbox.storage import ElasticsearchStorageHandler

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


async def get_env() -> Settings:
    return Settings()


async def get_elasticsearch_client(env: Annotated[Settings, Depends(get_env)]) -> Elasticsearch:
    return env.elasticsearch_client()


async def get_embedding_model(env: Annotated[Settings, Depends(get_env)]) -> Embeddings:
    embedding_model = SentenceTransformerEmbeddings(model_name=env.embedding_model, cache_folder=MODEL_PATH)
    log.info("Loaded embedding model from environment: %s", env.embedding_model)
    return embedding_model


async def get_storage_handler(
    es: Annotated[Elasticsearch, Depends(get_elasticsearch_client)],
    env: Annotated[Settings, Depends(get_env)],
) -> ElasticsearchStorageHandler:
    return ElasticsearchStorageHandler(es_client=es, root_index=env.elastic_root_index)


async def get_vector_store(
    env: Annotated[Settings, Depends(get_env)],
    es: Annotated[Elasticsearch, Depends(get_elasticsearch_client)],
    embedding_model: Annotated[Embeddings, Depends(get_embedding_model)],
) -> ElasticsearchStore:
    if env.elastic.subscription_level == "basic":
        strategy = ApproxRetrievalStrategy(hybrid=False)
    elif env.elastic.subscription_level in ["platinum", "enterprise"]:
        strategy = ApproxRetrievalStrategy(hybrid=True)
    else:
        message = f"Unknown Elastic subscription level {env.elastic.subscription_level}"
        raise ValueError(message)

    return ElasticsearchStore(
        es_connection=es,
        index_name=f"{env.elastic_root_index}-chunk",
        embedding=embedding_model,
        strategy=strategy,
        vector_query_field="embedding",
    )


async def get_llm(env: Annotated[Settings, Depends(get_env)]) -> ChatLiteLLM:
    # Create the appropriate LLM, either openai, Azure, anthropic or bedrock
    if env.openai_api_key is not None:
        log.info("Creating OpenAI LLM Client")
        llm = ChatLiteLLM(
            streaming=True,
            openai_key=env.openai_api_key,
        )
    elif env.azure_openai_api_key is not None:
        log.info("Creating Azure LLM Client")
        log.info("api_base: %s", env.azure_openai_endpoint)
        log.info("api_version: %s", env.openai_api_version)
        log.info("llm_max_tokens: %i", env.llm_max_tokens)

        # this nasty hack is required because, contrary to the docs:
        # using the api_version argument is not sufficient, and we need
        # to use the `OPENAI_API_VERSION` environment variable
        os.environ["OPENAI_API_VERSION"] = env.openai_api_version
        os.environ["AZURE_OPENAI_API_KEY"] = env.azure_openai_api_key

        llm = ChatLiteLLM(
            model=env.azure_openai_model,
            streaming=True,
            api_base=env.azure_openai_endpoint,
            max_tokens=env.llm_max_tokens,
        )
    elif env.anthropic_api_key is not None:
        msg = "anthropic LLM not yet implemented"
        log.exception(msg)
        raise ValueError(msg)
    else:
        msg = "Unknown LLM model specified or missing"
        log.exception(msg)
        raise ValueError(msg)
    return llm
