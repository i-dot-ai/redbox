from collections.abc import Generator
from pathlib import Path
from typing import TypeVar
from uuid import UUID, uuid4

import pytest
from botocore.exceptions import ClientError
from elasticsearch import Elasticsearch
from fastapi.testclient import TestClient
from jose import jwt

from core_api.src.app import app as application
from core_api.src.app import env
from redbox.models import Chunk, File
from redbox.storage import ElasticsearchStorageHandler

T = TypeVar("T")

YieldFixture = Generator[T, None, None]


@pytest.fixture()
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


@pytest.fixture()
def es_client() -> YieldFixture[Elasticsearch]:
    return env.elasticsearch_client()


@pytest.fixture()
def app_client() -> YieldFixture[TestClient]:
    return TestClient(application)


@pytest.fixture()
def alice() -> YieldFixture[UUID]:
    return uuid4()


@pytest.fixture()
def headers(alice):
    bearer_token = jwt.encode({"user_uuid": str(alice)}, key="nvjkernd")
    return {"Authorization": f"Bearer {bearer_token}"}


@pytest.fixture()
def elasticsearch_storage_handler(es_client):
    return ElasticsearchStorageHandler(es_client=es_client, root_index="redbox-data")


@pytest.fixture()
def file(s3_client, file_pdf_path: Path, alice) -> YieldFixture[File]:
    file_name = file_pdf_path.name
    file_type = file_pdf_path.suffix

    with file_pdf_path.open("rb") as f:
        s3_client.put_object(
            Bucket=env.bucket_name,
            Body=f.read(),
            Key=file_name,
            Tagging=f"file_type={file_type}",
        )

    file_record = File(key=file_name, bucket=env.bucket_name, creator_user_uuid=alice)

    return file_record


@pytest.fixture()
def stored_file(elasticsearch_storage_handler, file) -> YieldFixture[File]:
    elasticsearch_storage_handler.write_item(file)
    elasticsearch_storage_handler.refresh()
    return file


@pytest.fixture()
def chunked_file(elasticsearch_storage_handler, stored_file) -> YieldFixture[File]:
    for i in range(5):
        chunk = Chunk(
            text="hello",
            index=i,
            parent_file_uuid=stored_file.uuid,
            creator_user_uuid=stored_file.creator_user_uuid,
        )
        elasticsearch_storage_handler.write_item(chunk)
    elasticsearch_storage_handler.refresh()
    return stored_file


@pytest.fixture()
def file_pdf_path() -> Path:
    return Path(__file__).parents[2] / "tests" / "data" / "pdf" / "Cabinet Office - Wikipedia.pdf"
