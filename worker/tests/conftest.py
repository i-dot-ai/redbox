from pathlib import Path
from uuid import uuid4

import pytest
from botocore.exceptions import ClientError
from elasticsearch import Elasticsearch
from langchain_core.embeddings import Embeddings
from langchain_core.embeddings.fake import FakeEmbeddings

from redbox.models import File
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


@pytest.fixture(scope="session")
def file_pdf_path() -> Path:
    return Path(__file__).parents[2] / "tests" / "data" / "pdf" / "Cabinet Office - Wikipedia.pdf"


@pytest.fixture(scope="session")
def file(s3_client, file_pdf_path: Path):
    file_name = file_pdf_path.name
    file_type = file_pdf_path.suffix

    with file_pdf_path.open("rb") as f:
        s3_client.put_object(
            Bucket=env.bucket_name,
            Body=f.read(),
            Key=file_name,
            Tagging=f"file_type={file_type}",
        )

    return File(key=file_name, bucket=env.bucket_name, creator_user_uuid=uuid4())


@pytest.fixture(scope="session")
def bad_file(s3_client):
    s3_client.put_object(
        Bucket=env.bucket_name,
        Body=b"i am bytes, fear my wrath!",
        Key="bad-file.pdf",
        Tagging="file_type=pdf",
    )

    return File(key="bad-file.pdf", bucket=env.bucket_name, creator_user_uuid=uuid4())
