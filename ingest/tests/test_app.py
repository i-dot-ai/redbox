import os

import pytest
from sentence_transformers import SentenceTransformer

from ingest.src.app import FileIngestor
from redbox.models import File, Settings
from redbox.parsing.file_chunker import FileChunker
from redbox.storage import ElasticsearchStorageHandler

env = Settings(
    object_store="minio",
    minio_host="localhost",
    elastic_host="localhost",
    embedding_model="paraphrase-albert-small-v2",
)


@pytest.fixture
def s3_client():
    yield env.s3_client()


@pytest.fixture
def es_client():
    yield env.elasticsearch_client()


@pytest.fixture
def embedding_model():
    yield SentenceTransformer(env.embedding_model)


@pytest.fixture
def file_pdf_path() -> str:
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
    """
    TODO: this is a cut and paste of core_api:create_upload_file
    When we come to test core_api we should think about
    the relationship between core_api and the ingest app
    """
    file_name = os.path.basename(file_pdf_path)
    file_type = file_name.split(".")[-1]
    body = open(file_pdf_path, "rb").read()

    s3_client.put_object(
        Bucket=env.bucket_name,
        Body=body,
        Key=file_name,
        Tagging=f"file_type={file_type}",
    )

    authenticated_s3_url = s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": env.bucket_name, "Key": file_name},
        ExpiresIn=3600,
    )

    # Strip off the query string (we don't need the keys)
    simple_s3_url = authenticated_s3_url.split("?")[0]
    file_record = File(
        name=file_name,
        path=simple_s3_url,
        type=file_type,
        creator_user_uuid="dev",
        storage_kind=env.object_store,
    )

    yield file_record


def test_ingest_file(s3_client, es_client, embedding_model, file):
    """
    Given that I have written a text File to s3
    When I call ingest_file
    I Expect to see this file to be chunked and written to Elasticsearch
    """

    storage_handler = ElasticsearchStorageHandler(
        es_client=es_client, root_index="redbox-data"
    )
    chunker = FileChunker(embedding_model=embedding_model)
    file_ingestor = FileIngestor(s3_client, chunker, storage_handler)
    chunks = file_ingestor.ingest_file(file)
    assert chunks
