import os
from typing import TypeVar, Generator

import pytest
from elasticsearch import Elasticsearch

from fastapi.testclient import TestClient
from redbox.models import File
from core_api.src.app import app as application, env
from redbox.storage import ElasticsearchStorageHandler

T = TypeVar("T")

YieldFixture = Generator[T, None, None]


@pytest.fixture
def s3_client():
    yield env.s3_client()


@pytest.fixture
def es_client() -> YieldFixture[Elasticsearch]:
    yield env.elasticsearch_client()


@pytest.fixture
def app_client():
    yield TestClient(application)


@pytest.fixture
def elasticsearch_storage_handler(es_client):
    yield ElasticsearchStorageHandler(es_client=es_client, root_index="redbox-data")


@pytest.fixture
def file(s3_client, file_pdf_path, bucket) -> YieldFixture[File]:
    """
    TODO: this is a cut and paste of core_api:create_upload_file
    When we come to test core_api we should think about
    the relationship between core_api and the ingest app
    """
    file_name = os.path.basename(file_pdf_path)
    file_type = file_name.split(".")[-1]

    with open(file_pdf_path, "rb") as f:
        s3_client.put_object(
            Bucket=bucket,
            Body=f.read(),
            Key=file_name,
            Tagging=f"file_type={file_type}",
        )

    authenticated_s3_url = s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": env.bucket_name, "Key": file_name},
        ExpiresIn=3600,
    )

    # Strip off the query string (we don't need the keys)
    simple_s3_url = authenticated_s3_url.split("?")[0]
    file_record = File(
        name=file_name,
        path=simple_s3_url,
        type=file_type,
        creator_user_uuid="dev",
        storage_kind=env.object_store,
    )

    yield file_record


@pytest.fixture
def stored_file(elasticsearch_storage_handler, file) -> YieldFixture[File]:
    elasticsearch_storage_handler.write_item(file)
    yield file


@pytest.fixture
def bucket(s3_client):
    buckets = s3_client.list_buckets()
    if not any(bucket["Name"] == env.bucket_name for bucket in buckets["Buckets"]):
        s3_client.create_bucket(Bucket=env.bucket_name)
    yield env.bucket_name


@pytest.fixture
def file_pdf_path() -> YieldFixture[str]:
    path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "..", "tests",
        "data",
        "pdf",
        "Cabinet Office - Wikipedia.pdf",
    )
    yield path


@pytest.fixture
def rabbitmq_connection():
    connection = env.blocking_connection()
    yield connection
    connection.close()


@pytest.fixture
def rabbitmq_channel(rabbitmq_connection):
    channel = rabbitmq_connection.channel()
    yield channel
    channel.close()
