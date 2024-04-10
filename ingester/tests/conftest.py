import os
from typing import Generator, TypeVar

import pytest
from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer

from ingester.src.worker import env
from redbox.models import File

T = TypeVar("T")

YieldFixture = Generator[T, None, None]


@pytest.fixture
def s3_client():
    yield env.s3_client()


@pytest.fixture
def es_client() -> YieldFixture[Elasticsearch]:
    yield env.elasticsearch_client()


@pytest.fixture
def embedding_model() -> YieldFixture[SentenceTransformer]:
    yield SentenceTransformer(env.embedding_model)


@pytest.fixture
def file_pdf_path() -> YieldFixture[str]:
    path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..",
        "..",
        "tests",
        "data",
        "pdf",
        "Cabinet Office - Wikipedia.pdf",
    )
    yield path


@pytest.fixture
def file(s3_client, file_pdf_path):
    file_name = os.path.basename(file_pdf_path)
    file_type = f'.{file_name.split(".")[-1]}'

    with open(file_pdf_path, "rb") as f:
        s3_client.put_object(
            Bucket=env.bucket_name,
            Body=f.read(),
            Key=file_name,
            Tagging=f"file_type={file_type}",
        )

    file_record = File(bucket=env.bucket_name, key=file_name)
    yield file_record
