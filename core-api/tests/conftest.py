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

# -------------------#
# Clients and tools #
# -------------------#


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


# ------#
# Data #
# ------#

# These fixtures describe an elasticsearch instance containing files and
# chunks for a single user, Alice.
#
# Alice has two files stored:
#     * A PDF file
#     * An HTML file
#
# For each of these files, the following should exist in Elastic:
#     * A single entry in a "file" index
#     * A set of chunks in the "chunk" index at the normal resolution
#     * A set of chunks in the "chunk" index at the largest resolution


@pytest.fixture(scope="session")
def alice() -> UUID:
    """Alice."""
    return uuid4()


@pytest.fixture()
def headers(alice: UUID) -> dict[str, str]:
    """Alice's headers."""
    bearer_token = jwt.encode({"user_uuid": str(alice)}, key="nvjkernd")
    return {"Authorization": f"Bearer {bearer_token}"}


@pytest.fixture()
def file_pdf_path() -> Path:
    """The path of Alice's PDF."""
    return Path(__file__).parents[2] / "tests" / "data" / "pdf" / "Cabinet Office - Wikipedia.pdf"


@pytest.fixture()
def file_pdf_object(file_pdf_path: Path, alice: UUID, env: Settings) -> File:
    """The unuploaded File object of Alice's PDF."""
    file_name = file_pdf_path.name
    return File(key=file_name, bucket=env.bucket_name, creator_user_uuid=alice)


@pytest.fixture()
def file_pdf_chunks(file_pdf_object: File) -> list[Document]:
    """The Document chunk objects of Alice's PDF."""
    normal_chunks = [
        Document(
            page_content="hello",
            metadata=ChunkMetadata(
                parent_file_uuid=str(file_pdf_object.uuid),
                index=i,
                file_name=file_pdf_object.key,
                creator_user_uuid=file_pdf_object.creator_user_uuid,
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
                parent_file_uuid=str(file_pdf_object.uuid),
                index=i,
                file_name=file_pdf_object.key,
                creator_user_uuid=file_pdf_object.creator_user_uuid,
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
def file_pdf(
    es_store: ElasticsearchStore,
    es_storage_handler: ElasticsearchStorageHandler,
    file_pdf_object: File,
    file_pdf_chunks: list[Document],
) -> File:
    """The File object of Alice's PDF, with all objects in the Elasticsearch index."""
    es_storage_handler.write_item(file_pdf_object)
    es_storage_handler.refresh()
    es_store.add_documents(file_pdf_chunks)
    return file_pdf_object


@pytest.fixture()
def file_html_path() -> Path:
    """The path of Alice's HTML."""
    return Path(__file__).parents[2] / "tests" / "data" / "pdf" / "example.html"


@pytest.fixture()
def file_html_object(file_html_path: Path, alice: UUID, env: Settings) -> File:
    """The unuploaded File object of Alice's HTML."""
    file_name = file_html_path.name
    return File(key=file_name, bucket=env.bucket_name, creator_user_uuid=alice)


@pytest.fixture()
def file_html_chunks(file_html_object: File) -> list[Document]:
    """The Document chunk objects of Alice's HTML."""
    normal_chunks = [
        Document(
            page_content="hello",
            metadata=ChunkMetadata(
                parent_file_uuid=str(file_html_object.uuid),
                index=i,
                file_name=file_html_object.key,
                creator_user_uuid=file_html_object.creator_user_uuid,
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
                parent_file_uuid=str(file_html_object.uuid),
                index=i,
                file_name=file_html_object.key,
                creator_user_uuid=file_html_object.creator_user_uuid,
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
def file_html(
    es_store: ElasticsearchStore,
    es_storage_handler: ElasticsearchStorageHandler,
    file_html_object: File,
    file_html_chunks: list[Document],
) -> File:
    """The File object of Alice's HTML, with all objects in the Elasticsearch index."""
    es_storage_handler.write_item(file_html_object)
    es_storage_handler.refresh()
    es_store.add_documents(file_html_chunks)
    return file_html_object
