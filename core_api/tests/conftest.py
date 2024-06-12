from pathlib import Path
from uuid import UUID, uuid4

import pytest
from botocore.exceptions import ClientError
from elasticsearch import Elasticsearch
from fastapi.testclient import TestClient
from jose import jwt
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.llms.fake import FakeListLLM
from langchain_elasticsearch import ApproxRetrievalStrategy, ElasticsearchStore

from core_api.src.app import app as application
from core_api.src.app import env
from redbox.model_db import MODEL_PATH
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
def stored_file_1(elasticsearch_storage_handler, file) -> File:
    elasticsearch_storage_handler.write_item(file)
    elasticsearch_storage_handler.refresh()
    return file


@pytest.fixture()
def embedding_model_dim(embedding_model) -> int:
    return len(embedding_model.embed_query("foo"))


@pytest.fixture()
def stored_file_chunks(stored_file_1) -> list[Chunk]:
    chunks: list[Chunk] = []
    for i in range(5):
        chunks.append(
            Chunk(
                text="hello",
                index=i,
                parent_file_uuid=stored_file_1.uuid,
                creator_user_uuid=stored_file_1.creator_user_uuid,
                embedding=[1] * 768,
                metadata={"parent_doc_uuid": str(stored_file_1.uuid)},
            )
        )
    return chunks


@pytest.fixture()
def other_stored_file_chunks(stored_file_1) -> list[Chunk]:
    new_uuid = uuid4()
    chunks: list[Chunk] = []
    for i in range(5):
        chunks.append(
            Chunk(
                text="hello",
                index=i,
                parent_file_uuid=new_uuid,
                creator_user_uuid=stored_file_1.creator_user_uuid,
                embedding=[1] * 768,
                metadata={"parent_doc_uuid": str(new_uuid), "other": None},
            )
        )
    return chunks


@pytest.fixture()
def chunked_file(elasticsearch_storage_handler, stored_file_chunks, stored_file_1) -> File:
    for chunk in stored_file_chunks:
        elasticsearch_storage_handler.write_item(chunk)
    elasticsearch_storage_handler.refresh()
    return stored_file_1


@pytest.fixture()
def file_pdf_path() -> Path:
    return Path(__file__).parents[2] / "tests" / "data" / "pdf" / "Cabinet Office - Wikipedia.pdf"


@pytest.fixture()
def mock_llm():
    return FakeListLLM(responses=["<<TESTING>>"] * 128)


@pytest.fixture()
def embedding_model() -> SentenceTransformerEmbeddings:
    return SentenceTransformerEmbeddings(model_name=env.embedding_model, cache_folder=MODEL_PATH)


@pytest.fixture()
def chunk_index_name():
    return f"{env.elastic_root_index}-chunk"


@pytest.fixture()
def vector_store(es_client, embedding_model):
    if env.elastic.subscription_level == "basic":
        strategy = ApproxRetrievalStrategy(hybrid=False)
    elif env.elastic.subscription_level in ["platinum", "enterprise"]:
        strategy = ApproxRetrievalStrategy(hybrid=True)
    else:
        message = f"Unknown Elastic subscription level {env.elastic.subscription_level}"
        raise ValueError(message)

    return ElasticsearchStore(
        es_connection=es_client,
        index_name=f"{env.elastic_root_index}-chunk",
        embedding=embedding_model,
        strategy=strategy,
        vector_query_field="embedding",
    )
