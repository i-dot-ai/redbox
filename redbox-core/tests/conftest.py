from typing import TYPE_CHECKING
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from _pytest.fixtures import FixtureRequest
from botocore.exceptions import ClientError
from elasticsearch import Elasticsearch
import tiktoken
from tiktoken.core import Encoding

from redbox.models import Settings

from collections.abc import Generator

from langchain_core.embeddings.fake import FakeEmbeddings
from langchain_elasticsearch import ElasticsearchStore

from redbox.retriever import AllElasticsearchRetriever, ParameterisedElasticsearchRetriever, MetadataRetriever
from redbox.test.data import RedboxChatTestCase
from tests.retriever.data import ALL_CHUNKS_RETRIEVER_CASES, PARAMETERISED_RETRIEVER_CASES, METADATA_RETRIEVER_CASES

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
def es_index_file(env: Settings) -> str:
    return f"{env.elastic_root_index}-file"


@pytest.fixture(scope="session")
def es_client(env: Settings, es_index: str, es_index_file: str) -> Elasticsearch:
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


@pytest.fixture(autouse=True, scope="session")
def create_index(env: Settings, es_index: str, es_index_file: str) -> Generator[None, None, None]:
    es = env.elasticsearch_client()
    if not es.indices.exists(index=es_index):
        es.indices.create(index=es_index)
    if not es.indices.exists(index=es_index_file):
        es.indices.create(index=es_index_file)
    yield
    es.indices.delete(index=es_index)
    es.indices.delete(index=es_index_file)


@pytest.fixture(scope="session")
def all_chunks_retriever(es_client: Elasticsearch, es_index: str) -> AllElasticsearchRetriever:
    return AllElasticsearchRetriever(
        es_client=es_client,
        index_name=es_index,
    )


@pytest.fixture(scope="session")
def parameterised_retriever(
    env: Settings, es_client: Elasticsearch, es_index: str, embedding_model: FakeEmbeddings
) -> ParameterisedElasticsearchRetriever:
    return ParameterisedElasticsearchRetriever(
        es_client=es_client,
        index_name=es_index,
        embedding_model=embedding_model,
        embedding_field_name=env.embedding_document_field_name,
    )


@pytest.fixture(scope="session")
def metadata_retriever(es_client: Elasticsearch, es_index: str) -> MetadataRetriever:
    return MetadataRetriever(es_client=es_client, index_name=es_index)


# -----#
# Data #
# -----#


@pytest.fixture()
def alice() -> UUID:
    return uuid4()


@pytest.fixture()
def bob() -> UUID:
    return uuid4()


@pytest.fixture()
def claire() -> UUID:
    return uuid4()


@pytest.fixture
def file_pdf_path() -> Path:
    return Path(__file__).parents[2] / "tests" / "data" / "pdf" / "Cabinet Office - Wikipedia.pdf"


@pytest.fixture()
def file(s3_client: S3Client, file_pdf_path: Path, alice: UUID, env: Settings) -> str:
    file_name = file_pdf_path.name
    file_type = file_pdf_path.suffix

    with file_pdf_path.open("rb") as f:
        s3_client.put_object(
            Bucket=env.bucket_name,
            Body=f.read(),
            Key=file_name,
            Tagging=f"file_type={file_type}",
        )

    return file_name


@pytest.fixture(params=ALL_CHUNKS_RETRIEVER_CASES)
def stored_file_all_chunks(
    request: FixtureRequest, es_vector_store: ElasticsearchStore
) -> Generator[RedboxChatTestCase, None, None]:
    test_case: RedboxChatTestCase = request.param
    doc_ids = es_vector_store.add_documents(test_case.docs)
    yield test_case
    es_vector_store.delete(doc_ids)


@pytest.fixture(params=PARAMETERISED_RETRIEVER_CASES)
def stored_file_parameterised(
    request: FixtureRequest, es_vector_store: ElasticsearchStore
) -> Generator[RedboxChatTestCase, None, None]:
    test_case: RedboxChatTestCase = request.param
    doc_ids = es_vector_store.add_documents(test_case.docs)
    yield test_case
    es_vector_store.delete(doc_ids)


@pytest.fixture(params=METADATA_RETRIEVER_CASES)
def stored_file_metadata(
    request: FixtureRequest, es_vector_store: ElasticsearchStore
) -> Generator[RedboxChatTestCase, None, None]:
    test_case: RedboxChatTestCase = request.param
    doc_ids = es_vector_store.add_documents(test_case.docs)
    yield test_case
    es_vector_store.delete(doc_ids)
