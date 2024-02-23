import os
from typing import Generator, TypeVar

import dotenv
import pytest
from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer

from redbox.models import Chunk
from redbox.storage.elasticsearch import ElasticsearchStorageHandler
from fastapi.testclient import TestClient


T = TypeVar("T")

YieldFixture = Generator[T, None, None]

env_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", ".env.example"
)
if not os.path.exists(env_path):
    raise Exception(".env.test not found!")

ENV = dotenv.dotenv_values(env_path)


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


@pytest.fixture
def client():
    from app.workers.embed.app import app as application

    yield TestClient(application)


@pytest.fixture
def example_modes():
    from app.workers.embed.app import models as db

    db["paraphrase-albert-small-v2"] = SentenceTransformer(
        model_name_or_path="paraphrase-albert-small-v2",
        cache_folder="./models",
    )
    yield db
