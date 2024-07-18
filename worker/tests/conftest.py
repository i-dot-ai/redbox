import pytest
from botocore.exceptions import ClientError
from elasticsearch import Elasticsearch
from langchain_core.embeddings import Embeddings
from langchain_core.embeddings.fake import FakeEmbeddings

from worker.app import env


@pytest.fixture(scope="session")
def s3_client():
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
def es_client() -> Elasticsearch:
    return env.elasticsearch_client()


@pytest.fixture()
def embedding_model() -> Embeddings:
    return FakeEmbeddings(size=3072)

