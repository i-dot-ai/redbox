from collections.abc import Generator
from typing import TYPE_CHECKING

import pytest
import tiktoken
from _pytest.fixtures import FixtureRequest
from botocore.exceptions import ClientError
from elasticsearch import Elasticsearch
from langchain_core.embeddings.fake import FakeEmbeddings
from langchain_elasticsearch import ElasticsearchStore
from tiktoken.core import Encoding

from redbox.models.settings import Settings
from redbox.retriever import DjangoFileRetriever
from redbox.test.data import RedboxChatTestCase
from tests.retriever.data import ALL_CHUNKS_RETRIEVER_CASES, METADATA_RETRIEVER_CASES, PARAMETERISED_RETRIEVER_CASES

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client
else:
    S3Client = object


# ------------------#
# Clients and tools #
# ------------------#


@pytest.fixture(scope="session")
def env() -> Settings:
    return Settings(django_secret_key="", postgres_password="")


@pytest.fixture(scope="session")
def s3_client(env: Settings) -> S3Client:
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
def tokeniser() -> Encoding:
    return tiktoken.get_encoding("cl100k_base")


@pytest.fixture(scope="session")
def embedding_model_dim() -> int:
    return 3072  # 3-large default size


@pytest.fixture(scope="session")
def embedding_model(embedding_model_dim: int) -> FakeEmbeddings:
    return FakeEmbeddings(size=embedding_model_dim)


@pytest.fixture(scope="session")
def es_index(env: Settings) -> str:
    return f"{env.elastic_root_index}-chunk"


@pytest.fixture(scope="session")
def es_client(env: Settings) -> Elasticsearch:
    return env.elasticsearch_client()


@pytest.fixture(scope="session")
def es_vector_store(
    es_client: Elasticsearch, es_index: str, embedding_model: FakeEmbeddings, env: Settings
) -> ElasticsearchStore:
    return ElasticsearchStore(
        index_name=es_index,
        es_connection=es_client,
        query_field="text",
        vector_query_field=env.embedding_document_field_name,
        embedding=embedding_model,
    )


class FakeFile:
    def __init__(self, text, metadata):
        self.text = text
        self.token_count = metadata["token_count"]
        self.url = metadata["uri"]


class FileManager:
    def __init__(self, docs):
        self.docs = docs

    def filter(self, original_file__in, text__isnull, metadata__isnull):
        for doc in self.docs:
            yield FakeFile(doc.page_content, doc.metadata)


# -----#
# Data #
# -----#


@pytest.fixture(params=ALL_CHUNKS_RETRIEVER_CASES)
def stored_file_all_chunks(request: FixtureRequest) -> Generator[RedboxChatTestCase, None, None]:
    test_case: RedboxChatTestCase = request.param
    retriever = DjangoFileRetriever(file_manager=FileManager(test_case.docs))
    yield test_case, retriever


@pytest.fixture(params=PARAMETERISED_RETRIEVER_CASES)
def stored_file_parameterised(request: FixtureRequest) -> Generator[RedboxChatTestCase, None, None]:
    test_case: RedboxChatTestCase = request.param
    retriever = DjangoFileRetriever(file_manager=FileManager(test_case.docs))
    yield test_case, retriever


@pytest.fixture(params=METADATA_RETRIEVER_CASES)
def stored_file_metadata(request: FixtureRequest) -> Generator[RedboxChatTestCase, None, None]:
    test_case: RedboxChatTestCase = request.param
    retriever = DjangoFileRetriever(file_manager=FileManager(test_case.docs))
    yield test_case, retriever
