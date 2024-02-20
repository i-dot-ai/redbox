from typing import Generator, TypeVar

import dotenv
import pytest
from elasticsearch import Elasticsearch

from redbox.models import Chunk
from redbox.storage.elasticsearch import ElasticsearchStorageHandler

T = TypeVar("T")

YieldFixture = Generator[T, None, None]

ENV = dotenv.dotenv_values(".env.test")


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
                "host": ENV["ELASTIC_HOST"],
                "port": int(ENV["ELASTIC_PORT"]),
                "scheme": ENV["ELASTIC_SCHEME"],
            }
        ],
        basic_auth=(ENV["ELASTIC_USER"], ENV["ELASTIC_PASSWORD"]),
    )
    yield client


@pytest.fixture
def elasticsearch_storage_handler(elasticsearch_client):
    yield ElasticsearchStorageHandler(
        es_client=elasticsearch_client, root_index="redbox-test-data"
    )
