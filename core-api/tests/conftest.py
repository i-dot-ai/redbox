import time
from pathlib import Path
from uuid import UUID, uuid4
from datetime import UTC, datetime

import pytest
from botocore.exceptions import ClientError
from elasticsearch import Elasticsearch
from fastapi.testclient import TestClient
from jose import jwt
from langchain_core.documents.base import Document
from langchain_elasticsearch.vectorstores import ElasticsearchStore
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.llms.fake import FakeListLLM
from langchain_core.embeddings.fake import FakeEmbeddings

from core_api.app import app as application
from redbox.retriever import AllElasticsearchRetriever
from redbox.models import File, Settings
from redbox.models.file import ChunkMetadata, ChunkResolution
from redbox.storage import ElasticsearchStorageHandler


@pytest.fixture(scope="session")
def env():
    return Settings()


@pytest.fixture(scope="session")
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


@pytest.fixture(scope="session")
def es_client(env) -> Elasticsearch:
    return env.elasticsearch_client()


@pytest.fixture(scope="session")
def es_index(env) -> str:
    return f"{env.elastic_root_index}-chunk"


@pytest.fixture(scope="session")
def elasticsearch_store(es_index, es_client, embedding_model, env: Settings) -> str:
    return ElasticsearchStore(
        index_name=es_index,
        embedding=embedding_model,
        es_connection=es_client,
        vector_query_field=env.embedding_document_field_name
    )


@pytest.fixture()
def app_client() -> TestClient:
    return TestClient(application)


@pytest.fixture(scope="session")
def alice() -> UUID:
    return uuid4()


@pytest.fixture()
def headers(alice):
    bearer_token = jwt.encode({"user_uuid": str(alice)}, key="nvjkernd")
    return {"Authorization": f"Bearer {bearer_token}"}


@pytest.fixture()
def elasticsearch_storage_handler(es_client, env):
    return ElasticsearchStorageHandler(es_client=es_client, root_index=env.elastic_root_index)


@pytest.fixture()
def file(s3_client, file_pdf_path: Path, alice, env) -> File:
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
def large_stored_file(elasticsearch_storage_handler, file) -> File:
    elasticsearch_storage_handler.write_item(file)
    elasticsearch_storage_handler.refresh()
    return file


@pytest.fixture()
def stored_file_1(elasticsearch_storage_handler, file) -> File:
    elasticsearch_storage_handler.write_item(file)
    elasticsearch_storage_handler.refresh()
    return file


@pytest.fixture(scope="session")
def embedding_model_dim() -> int:
    return 3072  # 3-large default size


@pytest.fixture()
def stored_file_chunks(stored_file_1) -> list[Document]:
    normal_chunks = [
        Document(
            page_content="hello",
            metadata=ChunkMetadata(
                parent_file_uuid=str(stored_file_1.uuid),
                index=i,
                creator_user_uuid=stored_file_1.creator_user_uuid,
                page_number=4,
                created_datetime=datetime.now(UTC),
                token_count=4,
                chunk_resolution=ChunkResolution.normal              
            ).model_dump()
        )
        for i in range(10)
    ]

    large_chunks = [
        Document(
            page_content="hello"*10,
            metadata=ChunkMetadata(
                parent_file_uuid=str(stored_file_1.uuid),
                index=i,
                creator_user_uuid=stored_file_1.creator_user_uuid,
                page_number=4,
                created_datetime=datetime.now(UTC),
                token_count=20,
                chunk_resolution=ChunkResolution.largest              
            ).model_dump()
        )
        for i in range(2)
    ]
    return normal_chunks + large_chunks


@pytest.fixture()
def stored_large_file_chunks(stored_file_1) -> list[Document]:
    normal_chunks = [
        Document(
            page_content="hello",
            metadata=ChunkMetadata(
                parent_file_uuid=str(stored_file_1.uuid),
                index=i,
                creator_user_uuid=stored_file_1.creator_user_uuid,
                page_number=4,
                created_datetime=datetime.now(UTC),
                token_count=4,
                chunk_resolution=ChunkResolution.normal              
            ).model_dump()
        )
        for i in range(25)
    ]

    large_chunks = [
        Document(
            page_content="hello"*10,
            metadata=ChunkMetadata(
                parent_file_uuid=str(stored_file_1.uuid),
                index=i,
                creator_user_uuid=stored_file_1.creator_user_uuid,
                page_number=4,
                created_datetime=datetime.now(UTC),
                token_count=20,
                chunk_resolution=ChunkResolution.largest              
            ).model_dump()
        )
        for i in range(5)
    ]
    return normal_chunks + large_chunks


@pytest.fixture()
def chunked_file(elasticsearch_store: ElasticsearchStore, stored_file_chunks, stored_file_1) -> File:
    elasticsearch_store.add_documents(stored_file_chunks)
    return stored_file_1


@pytest.fixture()
def large_chunked_file(elasticsearch_store, stored_large_file_chunks, stored_file_1) -> File:
    elasticsearch_store.add_documents(stored_large_file_chunks)
    return stored_file_1


@pytest.fixture()
def file_pdf_path() -> Path:
    return Path(__file__).parents[2] / "tests" / "data" / "pdf" / "Cabinet Office - Wikipedia.pdf"


@pytest.fixture()
def mock_llm():
    return FakeListLLM(responses=["<<TESTING>>"] * 128)


@pytest.fixture(scope="session")
def embedding_model(embedding_model_dim) -> SentenceTransformerEmbeddings:
    return FakeEmbeddings(size=embedding_model_dim)


@pytest.fixture()
def all_chunks_retriever(es_client, es_index) -> AllElasticsearchRetriever:
    return AllElasticsearchRetriever(
        es_client=es_client,
        index_name=es_index,
    )
