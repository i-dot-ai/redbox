from pathlib import Path
from uuid import uuid4

import pytest
from botocore.exceptions import ClientError
from elasticsearch import Elasticsearch

from redbox.models import Chunk, File, Settings
from redbox.storage.elasticsearch import ElasticsearchStorageHandler

import time
from collections.abc import Generator

from langchain_core.documents.base import Document
from langchain_core.embeddings.fake import FakeEmbeddings
from langchain_core.runnables import ConfigurableField
from langchain_elasticsearch import ElasticsearchStore

from redbox.retriever import AllElasticsearchRetriever, ParameterisedElasticsearchRetriever
from tests.retriever.data import ALL_CHUNKS_RETRIEVER_DOCUMENTS, PARAMETERISED_RETRIEVER_DOCUMENTS


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

    return File(
        key=file_name,
        bucket=env.bucket_name,
        creator_user_uuid=alice,
    )


@pytest.fixture()
def chunk_belonging_to_alice(file_belonging_to_alice) -> Chunk:
    return Chunk(
        creator_user_uuid=file_belonging_to_alice.creator_user_uuid,
        parent_file_uuid=file_belonging_to_alice.uuid,
        index=1,
        text="hello, i am Alice!",
    )


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

    return File(
        key=file_name,
        bucket=env.bucket_name,
        creator_user_uuid=bob,
    )


@pytest.fixture()
def chunk_belonging_to_bob(file_belonging_to_bob) -> Chunk:
    return Chunk(
        creator_user_uuid=file_belonging_to_bob.creator_user_uuid,
        parent_file_uuid=file_belonging_to_bob.uuid,
        index=1,
        text="hello, i am Bob!",
    )


@pytest.fixture()
def chunk_belonging_to_claire(claire) -> Chunk:
    return Chunk(
        creator_user_uuid=claire,
        parent_file_uuid=uuid4(),
        index=1,
        text="hello, i am Claire!",
    )


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
def elasticsearch_storage_handler(elasticsearch_client, env) -> ElasticsearchStorageHandler:
    return ElasticsearchStorageHandler(es_client=elasticsearch_client, root_index=env.elastic_root_index)


@pytest.fixture()
def es_index(env) -> str:
    return f"{env.elastic_root_index}-chunk"


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
def stored_file_1(elasticsearch_storage_handler, file) -> File:
    elasticsearch_storage_handler.write_item(file)
    elasticsearch_storage_handler.refresh()
    return file


@pytest.fixture()
def embedding_model_dim() -> int:
    return 3072  # 3-large default size


@pytest.fixture()
def stored_file_chunks(stored_file_1, embedding_model_dim) -> list[Chunk]:
    chunks: list[Chunk] = []
    for i in range(5):
        chunks.append(
            Chunk(
                text="hello",
                index=i,
                embedding=[1] * embedding_model_dim,
                parent_file_uuid=stored_file_1.uuid,
                creator_user_uuid=stored_file_1.creator_user_uuid,
                metadata={"parent_doc_uuid": str(stored_file_1.uuid)},
            )
        )
    return chunks


@pytest.fixture(params=ALL_CHUNKS_RETRIEVER_DOCUMENTS)
def stored_file_all_chunks(
    request, elasticsearch_client, es_index, embedding_model_dim
) -> Generator[list[Document], None, None]:
    store = ElasticsearchStore(
        index_name=es_index,
        es_connection=elasticsearch_client,
        query_field="text",
        embedding=FakeEmbeddings(size=embedding_model_dim),
    )
    documents = list(map(Document.parse_obj, request.param))
    doc_ids = store.add_documents(documents)
    yield documents
    store.delete(doc_ids)


@pytest.fixture(params=PARAMETERISED_RETRIEVER_DOCUMENTS)
def stored_file_parameterised(request, elasticsearch_client, es_index) -> Generator[list[Document], None, None]:
    store = ElasticsearchStore(index_name=es_index, es_connection=elasticsearch_client, query_field="text")
    documents = list(map(Document.parse_obj, request.param))
    doc_ids = store.add_documents(documents)
    yield documents
    store.delete(doc_ids)


@pytest.fixture()
def chunked_file(elasticsearch_storage_handler, stored_file_chunks, stored_file_1) -> File:
    for chunk in stored_file_chunks:
        elasticsearch_storage_handler.write_item(chunk)
    elasticsearch_storage_handler.refresh()
    time.sleep(1)
    return stored_file_1


@pytest.fixture()
def all_chunks_retriever(elasticsearch_client, es_index) -> AllElasticsearchRetriever:
    return AllElasticsearchRetriever(
        es_client=elasticsearch_client,
        index_name=es_index,
    )


@pytest.fixture()
def parameterised_retriever(
    env, elasticsearch_client, es_index, embedding_model_dim
) -> ParameterisedElasticsearchRetriever:
    default_params = {
        "size": env.ai.rag_k,
        "num_candidates": env.ai.rag_num_candidates,
        "match_boost": 1,
        "knn_boost": 1,
        "similarity_threshold": 0,
    }
    return ParameterisedElasticsearchRetriever(
        es_client=elasticsearch_client,
        index_name=es_index,
        params=default_params,
        embedding_model=FakeEmbeddings(size=embedding_model_dim),
        embedding_field_name=env.embedding_document_field_name,
    ).configurable_fields(
        params=ConfigurableField(
            id="params", name="Retriever parameters", description="A dictionary of parameters to use for the retriever."
        )
    )
