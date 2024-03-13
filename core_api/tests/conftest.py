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


assert env.elastic_port == 9200


@pytest.fixture
def s3_client():
    yield env.s3_client()


@pytest.fixture
def es_client() -> YieldFixture[Elasticsearch]:
    yield env.elasticsearch_client()


@pytest.fixture
def client():
    yield TestClient(application)


@pytest.fixture
def elasticsearch_storage_handler(es_client):
    yield ElasticsearchStorageHandler(es_client=es_client, root_index="redbox-data")


@pytest.fixture
def file():
    yield File(name="my-file", path="users/my-file.txt", type="txt")


@pytest.fixture
def stored_file(elasticsearch_storage_handler, file):
    elasticsearch_storage_handler.write_item(item=file)
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
        "..",
        "..",
        "tests",
        "data",
        "pdf",
        "Cabinet Office - Wikipedia.pdf",
    )
    yield path
