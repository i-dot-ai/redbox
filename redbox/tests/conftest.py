from pathlib import Path
from uuid import uuid4

import pytest
from botocore.exceptions import ClientError
from elasticsearch import Elasticsearch

from redbox.models import Chunk, File, Settings
from redbox.storage.elasticsearch import ElasticsearchStorageHandler


@pytest.fixture()
def env():
    return Settings(django_secret_key="", postgres_password="")


@pytest.fixture()
def alice():
    return uuid4()


@pytest.fixture()
def bob():
    return uuid4()


@pytest.fixture()
def claire():
    return uuid4()


@pytest.fixture()
def file_belonging_to_alice(s3_client, file_pdf_path: Path, alice, env) -> File:
    file_name = file_pdf_path.name
    file_type = file_pdf_path.suffix

    with file_pdf_path.open("rb") as f:
        s3_client.put_object(
            Bucket=env.bucket_name,
            Body=f.read(),
            Key=file_name,
            Tagging=f"file_type={file_type}",
        )

    file_record = File(
        key=file_name,
        bucket=env.bucket_name,
        creator_user_uuid=alice,
    )

    return file_record


@pytest.fixture()
def chunk_belonging_to_alice(file_belonging_to_alice) -> Chunk:
    chunk = Chunk(
        creator_user_uuid=file_belonging_to_alice.creator_user_uuid,
        parent_file_uuid=file_belonging_to_alice.uuid,
        index=1,
        text="hello, i am Alice!",
    )
    return chunk


@pytest.fixture()
def file_belonging_to_bob(s3_client, file_pdf_path: Path, bob, env) -> File:
    file_name = file_pdf_path.name
    file_type = file_pdf_path.suffix

    with file_pdf_path.open("rb") as f:
        s3_client.put_object(
            Bucket=env.bucket_name,
            Body=f.read(),
            Key=file_name,
            Tagging=f"file_type={file_type}",
        )

    file_record = File(
        key=file_name,
        bucket=env.bucket_name,
        creator_user_uuid=bob,
    )

    return file_record


@pytest.fixture()
def chunk_belonging_to_bob(file_belonging_to_bob) -> Chunk:
    chunk = Chunk(
        creator_user_uuid=file_belonging_to_bob.creator_user_uuid,
        parent_file_uuid=file_belonging_to_bob.uuid,
        index=1,
        text="hello, i am Bob!",
    )
    return chunk


@pytest.fixture()
def chunk_belonging_to_claire(claire) -> Chunk:
    chunk = Chunk(
        creator_user_uuid=claire,
        parent_file_uuid=uuid4(),
        index=1,
        text="hello, i am Claire!",
    )
    return chunk


@pytest.fixture()
def file_pdf_path() -> Path:
    return Path(__file__).parents[2] / "tests" / "data" / "pdf" / "Cabinet Office - Wikipedia.pdf"


@pytest.fixture()
def s3_client(env):
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
def stored_chunk_belonging_to_alice(elasticsearch_storage_handler, chunk_belonging_to_alice) -> Chunk:
    elasticsearch_storage_handler.write_item(item=chunk_belonging_to_alice)
    elasticsearch_storage_handler.refresh()
    return chunk_belonging_to_alice


@pytest.fixture()
def stored_chunk_belonging_to_bob(elasticsearch_storage_handler, chunk_belonging_to_bob) -> Chunk:
    elasticsearch_storage_handler.write_item(item=chunk_belonging_to_bob)
    elasticsearch_storage_handler.refresh()
    return chunk_belonging_to_bob


@pytest.fixture()
def elasticsearch_client(env) -> Elasticsearch:
    return env.elasticsearch_client()


@pytest.fixture()
def elasticsearch_storage_handler(elasticsearch_client) -> ElasticsearchStorageHandler:
    return ElasticsearchStorageHandler(es_client=elasticsearch_client, root_index="redbox-test-data")
