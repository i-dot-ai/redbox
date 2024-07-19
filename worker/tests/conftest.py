import pytest
from botocore.exceptions import ClientError
from elasticsearch import Elasticsearch

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
