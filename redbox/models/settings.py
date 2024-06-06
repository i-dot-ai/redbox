import logging
from typing import Literal

import boto3
from elasticsearch import Elasticsearch
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


class ElasticLocalSettings(BaseModel):
    """settings required for a local/ec2 instance of elastic"""

    host: str = "elasticsearch"
    port: int = 9200
    scheme: str = "http"
    user: str = "elastic"
    version: str = "8.11.0"
    password: str = "redboxpass"
    subscription_level: str = "basic"


class ElasticCloudSettings(BaseModel):
    """settings required for elastic-cloud"""

    api_key: str
    cloud_id: str
    subscription_level: str = "basic"


class Settings(BaseSettings):
    """Settings for the redbox application."""

    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    azure_openai_api_key: str | None = None
    azure_openai_endpoint: str | None = None

    openai_api_version: str = "2023-12-01-preview"
    azure_openai_model: str = "azure/gpt-35-turbo-16k"

    partition_strategy: Literal["auto", "fast", "ocr_only", "hi_res"] = "fast"

    elastic: ElasticCloudSettings | ElasticLocalSettings = ElasticLocalSettings()
    elastic_root_index: str = "redbox-data"

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
    embedding_model: str = "all-mpnet-base-v2"

    embed_queue_name: str = "redbox-embedder-queue"
    ingest_queue_name: str = "redbox-ingester-queue"

    redis_host: str = "redis"
    redis_port: int = 6379

    object_store: str = "minio"

    dev_mode: bool = False
    superuser_email: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_nested_delimiter="__", extra="allow")

    def elasticsearch_client(self) -> Elasticsearch:
        if isinstance(self.elastic, ElasticLocalSettings):
            log.info("Connecting to self managed Elasticsearch")
            log.info("Elasticsearch host = %s", self.elastic.host)
            return Elasticsearch(
                hosts=[
                    {
                        "host": self.elastic.host,
                        "port": self.elastic.port,
                        "scheme": self.elastic.scheme,
                    }
                ],
                basic_auth=(self.elastic.user, self.elastic.password),
            )

        log.info("Connecting to Elastic Cloud Cluster")
        log.info("Cloud ID = %s", self.elastic.cloud_id)
        log.info("Elastic Cloud API Key = %s", self.elastic.api_key)

        return Elasticsearch(cloud_id=self.elastic.cloud_id, api_key=self.elastic.api_key)

    def s3_client(self):
        if self.object_store == "minio":
            client = boto3.client(
                "s3",
                aws_access_key_id=self.aws_access_key or "",
                aws_secret_access_key=self.aws_secret_key or "",
                endpoint_url=f"http://{self.minio_host}:{self.minio_port}",
            )

        elif self.object_store == "s3":
            client = boto3.client(
                "s3",
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_key,
                region_name=self.aws_region,
            )
        elif self.object_store == "moto":
            from moto import mock_aws

            mock = mock_aws()
            mock.start()

            client = boto3.client(
                "s3",
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_key,
                region_name=self.aws_region,
            )
        else:
            raise NotImplementedError

        return client

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/"
