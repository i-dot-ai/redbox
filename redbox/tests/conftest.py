from typing import Generator, TypeVar
from uuid import uuid4

import pytest
from elasticsearch import Elasticsearch

from redbox.models import Chunk, File, Settings
from redbox.storage.elasticsearch import ElasticsearchStorageHandler

T = TypeVar("T")

YieldFixture = Generator[T, None, None]


env = Settings()


@pytest.fixture
def chunk() -> Chunk:
    test_chunk = Chunk(
        parent_file_uuid=uuid4(),
        index=1,
        text="test_text",
        metadata={},
    )
    return test_chunk


@pytest.fixture
def file() -> File:
    test_file = File(
        name="test.pdf",
        url="http://example.com/test.pdf",
        status="uploaded",
        content_type="pdf",
    )
    return test_file


@pytest.fixture
def stored_chunk(elasticsearch_storage_handler, chunk) -> Chunk:
    elasticsearch_storage_handler.write_item(item=chunk)
    return chunk


@pytest.fixture
def elasticsearch_client() -> YieldFixture[Elasticsearch]:
    yield env.elasticsearch_client()


@pytest.fixture
def elasticsearch_storage_handler(elasticsearch_client):
    yield ElasticsearchStorageHandler(
        es_client=elasticsearch_client, root_index="redbox-test-data"
    )
