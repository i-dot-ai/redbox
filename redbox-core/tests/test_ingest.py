import json
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest
from _pytest.monkeypatch import MonkeyPatch
from elasticsearch import Elasticsearch
from elasticsearch.helpers import scan
from langchain_core.embeddings.fake import FakeEmbeddings
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_elasticsearch import ElasticsearchStore

import redbox
import redbox.loader
import redbox.loader.loaders
from redbox.chains.ingest import document_loader, ingest_from_loader
from redbox.loader import ingester
from redbox.loader.ingester import ingest_file
from redbox.loader.loaders import UnstructuredChunkLoader, coerce_to_string_list
from redbox.models.file import ChunkResolution
from redbox.models.settings import Settings
from redbox.retriever.queries import build_query_filter

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client
else:
    S3Client = object


def file_to_s3(filename: str, s3_client: S3Client, env: Settings) -> str:
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

    return file_name


def make_file_query(
    file_name: str, resolution: ChunkResolution | None = None
) -> dict[str, Any]:
    query_filter = build_query_filter(
        selected_files=[file_name],
        permitted_files=[file_name],
        chunk_resolution=resolution,
    )
    return {"query": {"bool": {"must": [{"match_all": {}}], "filter": query_filter}}}


@patch("redbox.loader.loaders.get_chat_llm")
@pytest.mark.parametrize(
    "fake_llm_response",
    [
        {
            "name": "foo",
            "description": "more test",
            "keywords": "hello, world",
        }
    ],
)
@patch("redbox.loader.loaders.requests.post")
def test_document_loader(
    mock_post: MagicMock,
    mock_llm: MagicMock,
    s3_client: S3Client,
    env: Settings,
    fake_llm_response: dict,
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

    mock_llm_response = mock_llm.return_value
    mock_llm_response.return_value = GenericFakeChatModel(
        messages=iter([json.dumps(fake_llm_response)])
    )

    loader = UnstructuredChunkLoader(
        chunk_resolution=ChunkResolution.normal,
        env=env,
        min_chunk_size=env.worker_ingest_min_chunk_size,
        max_chunk_size=env.worker_ingest_max_chunk_size,
    )

    # Upload file and and call
    file = file_to_s3("html/example.html", s3_client, env)
    loader = document_loader(loader, s3_client, env)
    chunks = list(loader.invoke(file))

    assert len(chunks) > 0

    # Verify that metadata has been attached to object
    for chuck in chunks:
        assert chuck.metadata["name"] == fake_llm_response["name"]
        assert chuck.metadata["description"] == fake_llm_response["description"]
        assert chuck.metadata["keywords"] == coerce_to_string_list(
            fake_llm_response["keywords"]
        )


@patch("redbox.loader.loaders.requests.post")
@pytest.mark.parametrize(
    "resolution, has_embeddings",
    [
        (ChunkResolution.normal, True),
        (ChunkResolution.largest, False),
    ],
)
def test_ingest_from_loader(
    mock_post: MagicMock,
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

    loader = UnstructuredChunkLoader(
        chunk_resolution=resolution,
        env=env,
        min_chunk_size=env.worker_ingest_min_chunk_size,
        max_chunk_size=env.worker_ingest_max_chunk_size,
    )

    # Mock embeddings
    monkeypatch.setattr(ingester, "get_embeddings", lambda _: FakeEmbeddings(size=3072))

    # Upload file and call
    file_name = file_to_s3(filename="html/example.html", s3_client=s3_client, env=env)
    ingest_chain = ingest_from_loader(
        loader=loader, s3_client=s3_client, vectorstore=es_vector_store, env=env
    )

    _ = ingest_chain.invoke(file_name)

    # Test it's written to Elastic
    file_query = make_file_query(file_name=file_name, resolution=resolution)

    chunks = list(
        scan(
            client=es_client, index=f"{env.elastic_root_index}-chunk", query=file_query
        )
    )
    assert len(chunks) > 0

    if has_embeddings:
        embeddings = chunks[0]["_source"].get("embedding")
        assert embeddings is not None
        assert len(embeddings) > 0

    # Teardown
    es_client.delete_by_query(index=f"{env.elastic_root_index}-chunk", body=file_query)


@patch("redbox.loader.loaders.get_chat_llm")
@pytest.mark.parametrize(
    "fake_llm_response",
    [
        [
            json.dumps(
                {
                    "name": "foo",
                    "description": "more test",
                    "keywords": "hello, world",
                },
                indent=4,
            ),
            json.dumps(
                {
                    "name": "bar",
                    "description": "blah blah",
                    "keywords": "bar, blah",
                },
                indent=4,
            ),
        ]
    ],
)
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
    mock_llm: MagicMock,
    es_client: Elasticsearch,
    s3_client: S3Client,
    monkeypatch: MonkeyPatch,
    env: Settings,
    filename: str,
    is_complete: bool,
    mock_json: list | None,
    fake_llm_response: list,
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
    filename = file_to_s3(filename=filename, s3_client=s3_client, env=env)

    # Mock llm
    mock_llm_response = mock_llm.return_value
    mock_llm_response.return_value = GenericFakeChatModel(
        messages=iter(fake_llm_response)
    )

    res = ingest_file(filename)

    if not is_complete:
        assert isinstance(res, str)
    else:
        assert res is None

        # Test it's written to Elastic
        file_query = make_file_query(file_name=filename)

        chunks = list(
            scan(
                client=es_client,
                index=f"{env.elastic_root_index}-chunk",
                query=file_query,
            )
        )
        assert len(chunks) > 0

        def get_metadata(chunk: dict) -> dict:
            return chunk["_source"]["metadata"]

        # Verify that metadata has been attached to document.
        for i, chunk in enumerate(chunks):
            metadata = get_metadata(chunk)
            fake_response = json.loads(fake_llm_response[i])
            assert metadata.get("name") == fake_response.get("name")
            assert metadata.get("description") == fake_response.get("description")
            assert metadata.get("keywords") == coerce_to_string_list(
                fake_response.get("keywords")
            )

        def get_chunk_resolution(chunk: dict) -> str:
            return chunk["_source"]["metadata"]["chunk_resolution"]

        normal_resolution = [
            chunk for chunk in chunks if get_chunk_resolution(chunk) == "normal"
        ]
        largest_resolution = [
            chunk for chunk in chunks if get_chunk_resolution(chunk) == "largest"
        ]

        assert len(normal_resolution) > 0
        assert len(largest_resolution) > 0

        # Teardown
        es_client.delete_by_query(
            index=f"{env.elastic_root_index}-chunk", body=file_query
        )
