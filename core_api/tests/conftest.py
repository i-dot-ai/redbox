from pathlib import Path
from uuid import UUID, uuid4

import pytest
from botocore.exceptions import ClientError
from elasticsearch import Elasticsearch
from fastapi.testclient import TestClient
from jose import jwt
from langchain_community.llms.fake import FakeListLLM

from core_api.src.app import app as application
from core_api.src.app import env
from redbox.models import Chunk, File
from redbox.storage import ElasticsearchStorageHandler


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
def es_client() -> Elasticsearch:
    return env.elasticsearch_client()


@pytest.fixture()
def app_client() -> TestClient:
    return TestClient(application)


@pytest.fixture()
def alice() -> UUID:
    return uuid4()


@pytest.fixture()
def headers(alice):
    bearer_token = jwt.encode({"user_uuid": str(alice)}, key="nvjkernd")
    return {"Authorization": f"Bearer {bearer_token}"}


@pytest.fixture()
def elasticsearch_storage_handler(es_client):
    return ElasticsearchStorageHandler(es_client=es_client, root_index=env.elastic_root_index)


@pytest.fixture()
def file(s3_client, file_pdf_path: Path, alice) -> File:
    file_name = file_pdf_path.name
    file_type = file_pdf_path.suffix

    with file_pdf_path.open("rb") as f:
        s3_client.put_object(
            Bucket=env.bucket_name,
            Body=f.read(),
            Key=file_name,
            Tagging=f"file_type={file_type}",
        )

    return File(key=file_name, bucket=env.bucket_name, creator_user_uuid=alice)


@pytest.fixture()
def stored_file(elasticsearch_storage_handler, file) -> File:
    elasticsearch_storage_handler.write_item(file)
    elasticsearch_storage_handler.refresh()
    return file


@pytest.fixture()
def stored_file_chunks(stored_file) -> list[Chunk]:
    chunks: list[Chunk] = []
    for i in range(5):
        chunks.append(
            Chunk(
                text="hello",
                index=i,
                parent_file_uuid=stored_file.uuid,
                creator_user_uuid=stored_file.creator_user_uuid,
            )
        )
    return chunks


@pytest.fixture()
def chunked_file(elasticsearch_storage_handler, stored_file_chunks, stored_file) -> File:
    for chunk in stored_file_chunks:
        elasticsearch_storage_handler.write_item(chunk)
    elasticsearch_storage_handler.refresh()
    return stored_file


@pytest.fixture()
def file_pdf_path() -> Path:
    return Path(__file__).parents[2] / "tests" / "data" / "pdf" / "Cabinet Office - Wikipedia.pdf"


@pytest.fixture()
def mock_llm():
    return FakeListLLM(responses=["<<TESTING>>"] * 128)
