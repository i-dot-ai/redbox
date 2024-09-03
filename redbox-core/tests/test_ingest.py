from typing import TYPE_CHECKING
from pathlib import Path
from typing import Any

import pytest
from _pytest.monkeypatch import MonkeyPatch
from langchain_core.embeddings.fake import FakeEmbeddings
from langchain_elasticsearch import ElasticsearchStore
from elasticsearch.helpers import scan
from elasticsearch import Elasticsearch
from unittest.mock import MagicMock, patch

from redbox.models.file import File

from redbox.loader import ingester
from redbox.loader.ingester import ingest_file
from redbox.chains.ingest import document_loader, ingest_from_loader
from redbox.loader.base import BaseRedboxFileLoader
from redbox.loader.loaders import UnstructuredTitleLoader
from redbox.loader.loaders import UnstructuredLargeChunkLoader
from redbox.models.settings import Settings
from redbox.retriever.queries import make_query_filter
from redbox.models.file import ChunkResolution

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client
else:
    S3Client = object


def file_to_s3(filename: str, s3_client: S3Client, env: Settings) -> File:
    file_path = Path(__file__).parents[2] / "tests" / "data" / filename
    file_name = file_path.name
    file_type = file_path.suffix

    with file_path.open("rb") as f:
        s3_client.put_object(
            Bucket=env.bucket_name,
            Body=f.read(),
            Key=file_name,
            Tagging=f"file_type={file_type}",
        )

    return File(key=file_name, bucket=env.bucket_name)


def make_file_query(file_name: str, resolution: ChunkResolution | None = None) -> dict[str, Any]:
    query_filter = make_query_filter([file_name], resolution)
    return {"query": {"bool": {"must": [{"match_all": {}}], "filter": query_filter}}}


@patch("redbox.loader.loaders.requests.post")
@pytest.mark.parametrize(
    "document_loader_type",
    [UnstructuredTitleLoader, UnstructuredLargeChunkLoader],
)
def test_document_loader(
    mock_post: MagicMock, document_loader_type: type[BaseRedboxFileLoader], s3_client: S3Client, env: Settings
):
    """
    Given that I have written a text File to s3
    When I call document_loader
    I Expect to see this file chunked and embedded if appropriate
    """
    # Mock call to Unstructured
    mock_response = mock_post.return_value
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {
            "type": "CompositeElement",
            "element_id": "1c493e1166a6e59ebe9e054c9c6c03db",
            "text": "Routing enables us to create bespoke responses according to user intent. Examples include:\n\n* RAG\n* Summarization\n* Plain chat",
            "metadata": {
                "languages": ["eng"],
                "orig_elements": "eJwVjsFOwzAQRH9l5SMiCEVtSXrjxI0D4lZVaGNPgtV4HdlrVKj679iXXe3szOidbgYrAkS/vDNHMnY89NPezd2Be9ft+mHfjfM4dOwwvDg4O++ezSOZAGXHyjVzMyvLUnhBrtfJQBZzvleP4qqtM8WiXhaC8LQiU8mkkWwCK2hC3uIFlNqWXN9sbUyuBaqrZCTyopXwiXDlsLUGL3YtDkd6oI/XtzpzCYET+z9WH6UK28peyH6zNlr93dBI3jml6vjBZ0O7n/8BhxNVfA==",
                "filename": "example.html",
                "filetype": "text/html",
            },
        }
    ]

    # Upload file and and call
    file = file_to_s3("html/example.html", s3_client, env)
    loader = document_loader(document_loader_type, s3_client, env)
    chunks = list(loader.invoke(file))

    assert len(chunks) > 0


@patch("redbox.loader.loaders.requests.post")
@pytest.mark.parametrize(
    "document_loader_type, resolution, has_embeddings",
    [
        (UnstructuredTitleLoader, ChunkResolution.normal, True),
        (UnstructuredLargeChunkLoader, ChunkResolution.largest, False),
    ],
)
def test_ingest_from_loader(
    mock_post: MagicMock,
    document_loader_type: type[BaseRedboxFileLoader],
    resolution: ChunkResolution,
    has_embeddings: bool,
    monkeypatch: MonkeyPatch,
    es_client: Elasticsearch,
    es_vector_store: ElasticsearchStore,
    s3_client: S3Client,
    env: Settings,
):
    """
    Given that I have written a text File to s3
    When I call ingest_from_loader
    I Expect to see this file chunked and embedded if appropriate
    """
    # Mock call to Unstructured
    mock_response = mock_post.return_value
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {
            "type": "CompositeElement",
            "element_id": "1c493e1166a6e59ebe9e054c9c6c03db",
            "text": "Routing enables us to create bespoke responses according to user intent. Examples include:\n\n* RAG\n* Summarization\n* Plain chat",
            "metadata": {
                "languages": ["eng"],
                "orig_elements": "eJwVjsFOwzAQRH9l5SMiCEVtSXrjxI0D4lZVaGNPgtV4HdlrVKj679iXXe3szOidbgYrAkS/vDNHMnY89NPezd2Be9ft+mHfjfM4dOwwvDg4O++ezSOZAGXHyjVzMyvLUnhBrtfJQBZzvleP4qqtM8WiXhaC8LQiU8mkkWwCK2hC3uIFlNqWXN9sbUyuBaqrZCTyopXwiXDlsLUGL3YtDkd6oI/XtzpzCYET+z9WH6UK28peyH6zNlr93dBI3jml6vjBZ0O7n/8BhxNVfA==",
                "filename": "example.html",
                "filetype": "text/html",
            },
        }
    ]

    # Mock embeddings
    monkeypatch.setattr(ingester, "get_embeddings", lambda _: FakeEmbeddings(size=3072))

    # Upload file and call
    file = file_to_s3(filename="html/example.html", s3_client=s3_client, env=env)
    ingest_chain = ingest_from_loader(
        document_loader_type=document_loader_type, s3_client=s3_client, vectorstore=es_vector_store, env=env
    )

    _ = ingest_chain.invoke(file)

    # Test it's written to Elastic
    file_query = make_file_query(file_name=file.key, resolution=resolution)

    chunks = list(scan(client=es_client, index=f"{env.elastic_root_index}-chunk", query=file_query))
    assert len(chunks) > 0

    if has_embeddings:
        embeddings = chunks[0]["_source"].get("embedding")
        assert embeddings is not None
        assert len(embeddings) > 0

    # Teardown
    es_client.delete_by_query(index=f"{env.elastic_root_index}-chunk", body=file_query)


@patch("redbox.loader.loaders.requests.post")
@pytest.mark.parametrize(
    ("filename", "is_complete", "mock_json"),
    [
        (
            "html/example.html",
            True,
            [
                {
                    "type": "CompositeElement",
                    "element_id": "1c493e1166a6e59ebe9e054c9c6c03db",
                    "text": "Routing enables us to create bespoke responses according to user intent. Examples include:\n\n* RAG\n* Summarization\n* Plain chat",
                    "metadata": {
                        "languages": ["eng"],
                        "orig_elements": "eJwVjsFOwzAQRH9l5SMiCEVtSXrjxI0D4lZVaGNPgtV4HdlrVKj679iXXe3szOidbgYrAkS/vDNHMnY89NPezd2Be9ft+mHfjfM4dOwwvDg4O++ezSOZAGXHyjVzMyvLUnhBrtfJQBZzvleP4qqtM8WiXhaC8LQiU8mkkWwCK2hC3uIFlNqWXN9sbUyuBaqrZCTyopXwiXDlsLUGL3YtDkd6oI/XtzpzCYET+z9WH6UK28peyH6zNlr93dBI3jml6vjBZ0O7n/8BhxNVfA==",
                        "filename": "example.html",
                        "filetype": "text/html",
                    },
                }
            ],
        ),
        ("html/corrupt.html", False, None),
    ],
)
def test_ingest_file(
    mock_post: MagicMock,
    es_client: Elasticsearch,
    s3_client: S3Client,
    monkeypatch: MonkeyPatch,
    env: Settings,
    filename: str,
    is_complete: bool,
    mock_json: list | None,
):
    """
    Given that I have written a text File to s3
    When I call ingest_file
    I Expect to see this file to be:
    1. chunked
    2. written to Elasticsearch
    """
    # Mock call to Unstructured
    mock_response = mock_post.return_value
    mock_response.status_code = 200
    mock_response.json.return_value = mock_json

    # Mock embeddings
    monkeypatch.setattr(ingester, "get_embeddings", lambda _: FakeEmbeddings(size=3072))

    # Upload file and call
    file = file_to_s3(filename=filename, s3_client=s3_client, env=env)

    res = ingest_file(file)

    if not is_complete:
        assert isinstance(res, str)
    else:
        assert res is None

        # Test it's written to Elastic
        file_query = make_file_query(file_name=file.key)

        chunks = list(scan(client=es_client, index=f"{env.elastic_root_index}-chunk", query=file_query))
        assert len(chunks) > 0

        def get_chunk_resolution(chunk: dict) -> str:
            return chunk["_source"]["metadata"]["chunk_resolution"]

        normal_resolution = [chunk for chunk in chunks if get_chunk_resolution(chunk) == "normal"]
        largest_resolution = [chunk for chunk in chunks if get_chunk_resolution(chunk) == "normal"]

        assert len(normal_resolution) > 0
        assert len(largest_resolution) > 0

        # Teardown
        es_client.delete_by_query(index=f"{env.elastic_root_index}-chunk", body=file_query)
