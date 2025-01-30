import logging
import os
from functools import cache, lru_cache

import boto3
from elasticsearch import Elasticsearch, ConnectionError
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
from langchain.globals import set_debug

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger()


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
    context_window_size: int = 128_000
    model_config = {"frozen": True}


class Settings(BaseSettings):
    """Settings for the redbox application."""

    elastic: ElasticCloudSettings | ElasticLocalSettings | None = None
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

    object_store: str = "minio"

    dev_mode: bool = False
    superuser_email: str | None = None

    system_prompt_template: str = """You are Redbox, an AI assistant to civil servants in the United Kingdom.

You follow instructions and respond to queries accurately and concisely, and are professional in all your
interactions with users. You use British English spellings and phrases rather than American English.

If you are provided with documents you use those as primary sources for information and use them to respond to the users queries
"""

    question_prompt_template: str = """
{% if documents is defined and documents|length > 0 %}
Documents:
{% for d in documents %}
Title: {{d.metadata.get("uri", "unknown document")}}
{{d.page_content}}

{% endfor %}
{% endif %}
Question: {{messages[-1].content}}
"""

    model_config = SettingsConfigDict(env_file=".env", env_nested_delimiter="__", extra="allow", frozen=True)

    @property
    def elastic_chat_mesage_index(self):
        return self.elastic_root_index + "-chat-mesage-log"

    @lru_cache(1)
    def elasticsearch_client(self) -> Elasticsearch:
        if self.elastic is None:
            return None

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

        else:
            client = Elasticsearch(cloud_id=self.elastic.cloud_id, api_key=self.elastic.api_key)

        try:
            if not client.indices.exists(index=self.elastic_chat_mesage_index):
                client.indices.create(index=self.elastic_chat_mesage_index)
        except ConnectionError:
            pass

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
