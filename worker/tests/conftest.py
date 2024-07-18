import pytest
from botocore.exceptions import ClientError
from elasticsearch import Elasticsearch
from langchain_core.embeddings import Embeddings
from langchain_core.embeddings.fake import FakeEmbeddings

from redbox.models import File
from redbox.models.settings import Settings


@pytest.fixture(scope="session")
def env():
    return Settings()


@pytest.fixture(scope="session")
def s3_client(env: Settings):
    _client = env.s3_client()
    try:
        _client.create_bucket(
            Bucket=env.bucket_name,
            CreateBucketConfiguration={"LocationConstraint": env.aws_region},
        )
    except ClientError as e:
        if e.response["Error"]["Code"] != "BucketAlreadyOwnedByYou":
            raise

    return _client


@pytest.fixture(scope="session")
def es_client(env: Settings) -> Elasticsearch:
    return env.elasticsearch_client()


@pytest.fixture(scope="session")
def es_index(env: Settings) -> str:
    return f"{env.elastic_root_index}-chunk"


@pytest.fixture(autouse=True, scope="session")
def create_index(env: Settings, es_index):
    es: Elasticsearch = env.elasticsearch_client()
    if not es.indices.exists(index=es_index):
        es.indices.create(index=es_index)
    yield
    es.indices.delete(index=es_index)


@pytest.fixture()
def embedding_model() -> Embeddings:
    return FakeEmbeddings(size=3072)
