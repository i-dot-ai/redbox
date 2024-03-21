
from typing import Literal, Optional

import boto3
import pika
from elasticsearch import Elasticsearch
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    elastic_host: str = "elasticsearch"
    elastic_port: int = 9200
    elastic_scheme: str = "http"
    elastic_user: str = "elastic"
    elastic_version: str = "8.11.0"
    elastic_password: str = "redboxpass"

    kibana_system_password: str = "redboxpass"
    metricbeat_internal_password: str = "redboxpass"
    filebeat_internal_password: str = "redboxpass"
    heartbeat_internal_password: str = "redboxpass"
    monitoring_internal_password: str = "redboxpass"
    beats_system_password: str = "redboxpass"

    minio_host: str = "minio"
    minio_port: int = 9000
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"

    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "eu-west-2"

    object_store: str = "minio"

    bucket_name: str = "redbox-storage-dev"
    embedding_model: str = "all-mpnet-base-v2"

    embed_queue_name: str = "redbox-embed-queue"
    ingest_queue_name: str = "redbox-ingest-queue"

    queue: str = "rabbitmq"

    rabbitmq_host: str = "rabbitmq"
    rabbitmq_port: int = 5672
    rabbitmq_user: str = "guest"
    rabbitmq_password: str = "guest"
    dev_mode: bool = False
    django_settings_module: str = "redbox_app.settings"
    debug: bool = True
    django_secret_key: str
    environment: Literal["LOCAL"] = "LOCAL"
    postgres_user: str = "redbox-core"
    postgres_db: str = "redbox-core"
    postgres_password: str
    postgres_host: str = "db"
    contact_email: str = "test@example.com"

    model_config = SettingsConfigDict(env_file=".env")

    def elasticsearch_client(self) -> Elasticsearch:
        es = Elasticsearch(
            hosts=[
                {
                    "host": self.elastic_host,
                    "port": self.elastic_port,
                    "scheme": self.elastic_scheme,
                }
            ],
            basic_auth=(self.elastic_user, self.elastic_password),
        )

        return es

    def s3_client(self):
        if self.object_store == "minio":
            client = boto3.client(
                "s3",
                aws_access_key_id=self.minio_access_key,
                aws_secret_access_key=self.minio_secret_key,
                endpoint_url=f"http://{self.minio_host}:{self.minio_port}",
            )
            return client

        if self.object_store == "s3":
            client = boto3.client(
                "s3",
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                region_name=self.aws_region,
            )
            return client

        raise NotImplementedError

    def sqs_client(self):
        sqs = boto3.client(
            "sqs",
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            region_name=self.aws_region,
        )
        return sqs

    def blocking_connection(self) -> pika.BlockingConnection:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=self.rabbitmq_host,
                port=self.rabbitmq_port,
                credentials=pika.PlainCredentials(self.rabbitmq_user, self.rabbitmq_password),
                connection_attempts=5,
                retry_delay=5,
            )
        )
        return connection

