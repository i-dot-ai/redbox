import logging
import os
from typing import Annotated, Any, TypedDict

from elasticsearch import Elasticsearch
from fastapi import Depends
from langchain_community.chat_models import ChatLiteLLM
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_core.embeddings import Embeddings
from langchain_elasticsearch import ElasticsearchRetriever
from langchain_elasticsearch import ApproxRetrievalStrategy, ElasticsearchStore
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
import numpy as np

from redbox.model_db import MODEL_PATH
from redbox.models import Settings
from redbox.models.file import UUID, Chunk
from redbox.models.chat import ChatRequest
from redbox.storage import ElasticsearchStorageHandler
from core_api.src.semantic_routes import (
    ABILITY_RESPONSE,
    COACH_RESPONSE,
    INFO_RESPONSE,
    route_layer,
)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


def get_env() -> Settings:
    return Settings()


def get_elasticsearch_client(env: Annotated[Settings, Depends(get_env)]) -> Elasticsearch:
    return env.elasticsearch_client()


def get_embedding_model(env: Annotated[Settings, Depends(get_env)]) -> Embeddings:
    embedding_model = SentenceTransformerEmbeddings(model_name=env.embedding_model, cache_folder=MODEL_PATH)
    log.info("Loaded embedding model from environment: %s", env.embedding_model)
    return embedding_model


async def get_storage_handler(
    es: Annotated[Elasticsearch, Depends(get_elasticsearch_client)],
    env: Annotated[Settings, Depends(get_env)],
) -> ElasticsearchStorageHandler:
    return ElasticsearchStorageHandler(es_client=es, root_index=env.elastic_root_index)


def get_vector_store(
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


class ESQuery(TypedDict):
    question: str
    file_uuids: list[UUID]
    user_uuid: UUID


def get_es_retriever(
    env: Annotated[Settings, Depends(get_env)],
    es: Elasticsearch = Depends(get_elasticsearch_client),
    embedding_model: SentenceTransformerEmbeddings = Depends(get_embedding_model),
) -> ElasticsearchRetriever:
    """Creates an Elasticsearch retriever runnable.

    Runnable takes input of a dict keyed to question, file_uuids and user_uuid.

    Runnable returns a list of Chunks.
    """

    def es_query(query: ESQuery) -> dict[str, Any]:
        vector = embedding_model.embed_query(query["question"])

        knn_filter = [{"term": {"creator_user_uuid.keyword": str(query["user_uuid"])}}]

        if len(query["file_uuids"]) != 0:
            knn_filter.append({"terms": {"parent_file_uuid.keyword": [str(uuid) for uuid in query["file_uuids"]]}})

        return {
            "size": 5,
            "query": {
                "bool": {
                    "must": [
                        {
                            "knn": {
                                "field": "embedding",
                                "query_vector": vector,
                                "num_candidates": 10,
                                "filter": knn_filter,
                            }
                        }
                    ]
                }
            },
        }

    def chunk_mapper(hit: dict[str, Any]) -> Chunk:
        return Chunk(**hit["_source"])

    return ElasticsearchRetriever(
        es_client=es, index_name=f"{env.elastic_root_index}-chunk", body_func=es_query, document_mapper=chunk_mapper
    )


def get_llm(env: Annotated[Settings, Depends(get_env)]) -> ChatLiteLLM:
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


# Hack before refactoring to dependency managed chains
es_retriever = get_es_retriever(get_env(), get_elasticsearch_client(get_env()), get_embedding_model(get_env()))
llm = get_llm(get_env())
