import os
from typing import TypeVar, Generator

import pytest
from elasticsearch import Elasticsearch

from fastapi.testclient import TestClient
from redbox.models import Settings, File
from core_api.src.app import app as application
from redbox.storage import ElasticsearchStorageHandler

T = TypeVar("T")

YieldFixture = Generator[T, None, None]

env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env.test")

env = Settings(  # type: ignore
    _env_file=env_path,
    object_store="minio",
    minio_host="localhost",
    elastic_host="localhost",
    embedding_model="paraphrase-albert-small-v2",
)


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
def elasticsearch_storage_handler(elasticsearch_client):
    yield ElasticsearchStorageHandler(es_client=elasticsearch_client, root_index="redbox-test-data")


@pytest.fixture
def file():
    yield File(name="my-file",
        path="users/my-file.txt",
        type="txt"
               )

@pytest.fixture
def stored_file(elasticsearch_storage_handler, file):
    elasticsearch_storage_handler.write_item(item=file)
    yield file

