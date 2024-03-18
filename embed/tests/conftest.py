from typing import Generator, TypeVar
from uuid import uuid4

import pytest
from elasticsearch import Elasticsearch
from fastapi.testclient import TestClient
from sentence_transformers import SentenceTransformer

from embed.src.app import app as application
from embed.src.app import model_db
from redbox.models import Chunk, EmbedQueueItem, Settings
from redbox.storage import ElasticsearchStorageHandler

T = TypeVar("T")

YieldFixture = Generator[T, None, None]


env = Settings()


@pytest.fixture
def client():
    yield TestClient(application)


@pytest.fixture
def example_model_db():
    model_db["paraphrase-albert-small-v2"] = SentenceTransformer(
        model_name_or_path="paraphrase-albert-small-v2",
        cache_folder="./models",
    )
    yield model_db


@pytest.fixture
def chunk() -> YieldFixture[Chunk]:
    test_chunk = Chunk(
        uuid=str(uuid4()),
        parent_file_uuid="test_uuid",
        index=1,
        text="test_text",
        metadata={},
        creator_user_uuid="test",
    )
    yield test_chunk


@pytest.fixture
def embed_queue_item(stored_chunk) -> YieldFixture[EmbedQueueItem]:
    yield EmbedQueueItem(model="paraphrase-albert-small-v2", chunk_uuid=stored_chunk.uuid)


@pytest.fixture
def elasticsearch_client() -> YieldFixture[Elasticsearch]:
    yield env.elasticsearch_client()


@pytest.fixture
def elasticsearch_storage_handler(elasticsearch_client) -> YieldFixture[ElasticsearchStorageHandler]:
    yield ElasticsearchStorageHandler(es_client=elasticsearch_client, root_index="redbox-test-data")


@pytest.fixture
def stored_chunk(chunk, elasticsearch_storage_handler) -> YieldFixture[Chunk]:
    elasticsearch_storage_handler.write_item(chunk)
    yield chunk
