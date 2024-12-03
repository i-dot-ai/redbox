import logging
import os
from functools import cache, lru_cache
from typing import Literal

import boto3
from elasticsearch import Elasticsearch
from opensearchpy import OpenSearch, RequestsHttpConnection
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
from langchain.globals import set_debug

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger()


class OpenSearchSettings(BaseModel):
    """settings required for a aws/opensearch"""

    model_config = SettingsConfigDict(frozen=True)

    collection_endpoint: str


class ElasticLocalSettings(BaseModel):
    """settings required for a local/ec2 instance of elastic"""

    model_config = SettingsConfigDict(frozen=True)

    host: str = "elasticsearch"
    port: int = 9200
    scheme: str = "http"
    user: str = "elastic"
    version: str = "8.11.0"
    password: str = "redboxpass"
    subscription_level: str = "basic"


class ElasticCloudSettings(BaseModel):
    """settings required for elastic-cloud"""

    model_config = SettingsConfigDict(frozen=True)

    api_key: str
    cloud_id: str
    subscription_level: str = "basic"


class ChatLLMBackend(BaseModel):
    name: str = "gpt-4o"
    provider: str = "azure_openai"
    description: str | None = None
    model_config = {"frozen": True}


class Settings(BaseSettings):
    """Settings for the redbox application."""

    embedding_openai_api_key: str = "NotAKey"
    embedding_azure_openai_endpoint: str = "not an endpoint"
    azure_api_version_embeddings: str = "2024-02-01"
    metadata_extraction_llm: ChatLLMBackend = ChatLLMBackend(name="gpt-4o", provider="azure_openai")

    embedding_backend: Literal[
        "text-embedding-ada-002",
        "amazon.titan-embed-text-v2:0",
        "text-embedding-3-large",
        "fake",
    ] = "text-embedding-3-large"

    llm_max_tokens: int = 1024

    embedding_max_retries: int = 1
    embedding_retry_min_seconds: int = 120  # Azure uses 60s
    embedding_retry_max_seconds: int = 300
    embedding_max_batch_size: int = 512
    embedding_document_field_name: str = "embedding"

    embedding_openai_base_url: str | None = None

    partition_strategy: Literal["auto", "fast", "ocr_only", "hi_res"] = "fast"
    clustering_strategy: Literal["full"] | None = None

    elastic: ElasticCloudSettings | ElasticLocalSettings | OpenSearchSettings = ElasticLocalSettings()
    elastic_root_index: str = "redbox-data"
    elastic_chunk_alias: str = "redbox-data-chunk-current"

    kibana_system_password: str = "redboxpass"
    metricbeat_internal_password: str = "redboxpass"
    filebeat_internal_password: str = "redboxpass"
    heartbeat_internal_password: str = "redboxpass"
    monitoring_internal_password: str = "redboxpass"
    beats_system_password: str = "redboxpass"

    minio_host: str = "minio"
    minio_port: int = 9000
    aws_access_key: str | None = None
    aws_secret_key: str | None = None

    aws_region: str = "eu-west-2"
    bucket_name: str = "redbox-storage-dev"

    ## Chunks
    ### Normal
    worker_ingest_min_chunk_size: int = 1_000
    worker_ingest_max_chunk_size: int = 10_000
    ### Largest
    worker_ingest_largest_chunk_size: int = 300_000
    worker_ingest_largest_chunk_overlap: int = 0

    response_no_doc_available: str = "No available data for selected files. They may need to be removed and added again"
    response_max_content_exceeded: str = "Max content exceeded. Try smaller or fewer documents"

    object_store: str = "minio"

    dev_mode: bool = False
    superuser_email: str | None = None

    unstructured_host: str = "unstructured"

    model_config = SettingsConfigDict(env_file=".env", env_nested_delimiter="__", extra="allow", frozen=True)

    ## Prompts
    metadata_prompt: tuple = (
        "system",
        "You are an SEO specialist that must optimise the metadata of a document "
        "to make it as discoverable as possible. You are about to be given the first "
        "1_000 tokens of a document and any hard-coded file metadata that can be "
        "recovered from it. Create SEO-optimised metadata for this document."
        "Description must be less than 100 words. and no more than 5 keywords .",
    )

    @property
    def elastic_chat_message_index(self):
        return self.elastic_root_index + "-chat-mesage-log"

    @property
    def elastic_user_index(self):
        return self.elastic_root_index + "-user-log"

    @property
    def elastic_alias(self):
        return self.elastic_root_index + "-chunk-current"

    @lru_cache(1)
    def elasticsearch_client(self) -> Elasticsearch:
        if isinstance(self.elastic, ElasticLocalSettings):
            client = Elasticsearch(
                hosts=[
                    {
                        "host": self.elastic.host,
                        "port": self.elastic.port,
                        "scheme": self.elastic.scheme,
                    }
                ],
                basic_auth=(self.elastic.user, self.elastic.password),
            )

        elif isinstance(self.elastic, OpenSearchSettings):
            client = OpenSearch(
                hosts=[{"host": self.elastic.collection_endpoint, "port": 443}],
                use_ssl=True,
                verify_certs=True,
                connection_class=RequestsHttpConnection,
                pool_maxsize=100,
            )

        else:
            client = Elasticsearch(cloud_id=self.elastic.cloud_id, api_key=self.elastic.api_key)

        if not client.indices.exists_alias(name=self.elastic_alias):
            chunk_index = f"{self.elastic_root_index}-chunk"
            client.options(ignore_status=[400]).indices.create(index=chunk_index)
            client.indices.put_alias(index=chunk_index, name=self.elastic_alias)

        for index in self.elastic_chat_message_index, self.elastic_user_index:
            if not client.indices.exists(index=index):
                client.indices.create(index=index)

        return client.options(request_timeout=30, retry_on_timeout=True, max_retries=3)

    def s3_client(self):
        if self.object_store == "minio":
            return boto3.client(
                "s3",
                aws_access_key_id=self.aws_access_key or "",
                aws_secret_access_key=self.aws_secret_key or "",
                endpoint_url=f"http://{self.minio_host}:{self.minio_port}",
            )

        if self.object_store == "s3":
            return boto3.client(
                "s3",
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_key,
                region_name=self.aws_region,
            )

        if self.object_store == "moto":
            from moto import mock_aws

            mock = mock_aws()
            mock.start()

            return boto3.client(
                "s3",
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_key,
                region_name=self.aws_region,
            )

        msg = f"unkown object_store={self.object_store}"
        raise NotImplementedError(msg)


@cache
def get_settings() -> Settings:
    s = Settings()
    set_debug(s.dev_mode)
    return s
