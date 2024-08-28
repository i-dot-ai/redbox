from datetime import UTC, datetime
from pathlib import Path
from typing import Generator
from uuid import UUID, uuid4

import pytest
from elasticsearch import Elasticsearch
from fastapi.testclient import TestClient
from jose import jwt
from langchain_core.documents.base import Document
from langchain_core.embeddings.fake import FakeEmbeddings
from langchain_elasticsearch.vectorstores import ElasticsearchStore
from redbox.models import File, Settings
from redbox.models.file import ChunkMetadata, ChunkResolution
from redbox.storage import ElasticsearchStorageHandler

from core_api import dependencies
from core_api.app import app as application
from core_api.routes.chat import chat_app

# Clients and tools


@pytest.fixture(scope="session")
def env() -> Settings:
    return Settings()


@pytest.fixture(scope="session")
def es_client(env: Settings) -> Elasticsearch:
    return env.elasticsearch_client()


@pytest.fixture()
def es_storage_handler(es_client: Elasticsearch, env: Settings) -> ElasticsearchStorageHandler:
    return ElasticsearchStorageHandler(es_client=es_client, root_index=env.elastic_root_index)


@pytest.fixture(scope="session")
def es_index(env: Settings) -> str:
    return f"{env.elastic_root_index}-chunk"


@pytest.fixture(autouse=True, scope="session")
def create_index(es_index: str, es_client: Elasticsearch):
    if not es_client.indices.exists(index=es_index):
        es_client.indices.create(index=es_index)
    yield
    es_client.indices.delete(index=es_index, ignore_unavailable=True)


@pytest.fixture(scope="session")
def embedding_model_dim() -> int:
    return 3072  # 3-large default size


@pytest.fixture(scope="session")
def embedding_model(embedding_model_dim: int) -> FakeEmbeddings:
    return FakeEmbeddings(size=embedding_model_dim)


@pytest.fixture(scope="session")
def es_store(es_index: str, es_client: Elasticsearch, embedding_model: FakeEmbeddings, env: Settings) -> str:
    return ElasticsearchStore(
        index_name=es_index,
        embedding=embedding_model,
        es_connection=es_client,
        vector_query_field=env.embedding_document_field_name,
    )


@pytest.fixture()
def app_client(embedding_model: FakeEmbeddings) -> Generator[TestClient, None, None]:
    chat_app.dependency_overrides[dependencies.get_embedding_model] = lambda: embedding_model
    yield TestClient(application)
    chat_app.dependency_overrides = {}


# Data


@pytest.fixture()
def file_pdf_path() -> Path:
    return Path(__file__).parents[2] / "tests" / "data" / "pdf" / "Cabinet Office - Wikipedia.pdf"


@pytest.fixture(scope="session")
def alice() -> UUID:
    return uuid4()


@pytest.fixture()
def headers(alice: UUID) -> dict[str, str]:
    bearer_token = jwt.encode({"user_uuid": str(alice)}, key="nvjkernd")
    return {"Authorization": f"Bearer {bearer_token}"}


@pytest.fixture()
def file(file_pdf_path: Path, alice: UUID, env: Settings) -> File:
    file_name = file_pdf_path.name
    return File(key=file_name, bucket=env.bucket_name, creator_user_uuid=alice)


@pytest.fixture()
def stored_file_1(es_storage_handler: ElasticsearchStorageHandler, file: File) -> File:
    es_storage_handler.write_item(file)
    es_storage_handler.refresh()
    return file


@pytest.fixture()
def stored_user_files(es_storage_handler: ElasticsearchStorageHandler) -> list[File]:
    user = uuid4()
    files = [
        File(creator_user_uuid=user, key="testfile1.txt", bucket="local"),
        File(creator_user_uuid=user, key="testfile2.txt", bucket="local"),
    ]
    for file in files:
        es_storage_handler.write_item(file)
    es_storage_handler.refresh()
    return files


@pytest.fixture()
def stored_file_chunks(stored_file_1: File) -> list[Document]:
    normal_chunks = [
        Document(
            page_content="hello",
            metadata=ChunkMetadata(
                parent_file_uuid=str(stored_file_1.uuid),
                index=i,
                file_name="test_file",
                creator_user_uuid=stored_file_1.creator_user_uuid,
                page_number=4,
                created_datetime=datetime.now(UTC),
                token_count=4,
                chunk_resolution=ChunkResolution.normal,
            ).model_dump(),
        )
        for i in range(10)
    ]

    large_chunks = [
        Document(
            page_content="hello" * 10,
            metadata=ChunkMetadata(
                parent_file_uuid=str(stored_file_1.uuid),
                index=i,
                file_name="test_file",
                creator_user_uuid=stored_file_1.creator_user_uuid,
                page_number=4,
                created_datetime=datetime.now(UTC),
                token_count=20,
                chunk_resolution=ChunkResolution.largest,
            ).model_dump(),
        )
        for i in range(2)
    ]
    return normal_chunks + large_chunks


@pytest.fixture()
def chunked_file(es_store: ElasticsearchStore, stored_file_chunks: list[Document], stored_file_1: File) -> File:
    es_store.add_documents(stored_file_chunks)
    return stored_file_1
