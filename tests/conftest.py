import os
from typing import Generator, TypeVar

import pytest
from elasticsearch import Elasticsearch

from redbox.models import Chunk, Settings
from redbox.storage.elasticsearch import ElasticsearchStorageHandler


T = TypeVar("T")

YieldFixture = Generator[T, None, None]

env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env.test")


env = Settings(_env_file=env_path)


@pytest.fixture
def chunk() -> Chunk:
    test_chunk = Chunk(
        uuid="aaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        parent_file_uuid="test_uuid",
        index=1,
        text="test_text",
        metadata={},
        creator_user_uuid="test",
    )
    return test_chunk


def file_pdf_path() -> str:
    return "tests/data/pdf/Cabinet Office - Wikipedia.pdf"


@pytest.fixture
def elasticsearch_client() -> YieldFixture[Elasticsearch]:
    client = Elasticsearch(
        hosts=[
            {
                "host": env.elastic_host,
                "port": env.elastic_port,
                "scheme": env.elastic_scheme,
            }
        ],
        basic_auth=(env.elastic_user, env.elastic_password),
    )
    yield client


@pytest.fixture
def elasticsearch_storage_handler(elasticsearch_client):
    yield ElasticsearchStorageHandler(
        es_client=elasticsearch_client, root_index="redbox-test-data"
    )
