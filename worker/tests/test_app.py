from pathlib import Path
from uuid import uuid4

import pytest
from faststream.redis import TestApp, TestRedisBroker
from langchain_core.embeddings.fake import FakeEmbeddings

from redbox.models.file import File, ProcessingStatusEnum
from redbox.storage import ElasticsearchStorageHandler
from worker.app import app, broker, env
from worker import app as app_module


@pytest.mark.asyncio()
@pytest.mark.parametrize(
    "filename, status",
    [
        ("Cabinet Office - Wikipedia.pdf", ProcessingStatusEnum.complete),
        ("Cabinet Office - Wikipedia.corrupt.pdf", ProcessingStatusEnum.failed),
    ],
)
async def test_ingest_file(es_client, s3_client, monkeypatch, filename: str, status: ProcessingStatusEnum):
    """
    Given that I have written a text File to s3
    When I call ingest_file
    I Expect to see this file to be:
    1. chunked
    2. written to Elasticsearch
    """

    pdf = Path(__file__).parents[2] / "tests" / "data" / "pdf" / filename
    file_name = pdf.name
    file_type = pdf.suffix

    with pdf.open("rb") as f:
        s3_client.put_object(
            Bucket=env.bucket_name,
            Body=f.read(),
            Key=file_name,
            Tagging=f"file_type={file_type}",
        )

    file = File(key=file_name, bucket=env.bucket_name, creator_user_uuid=uuid4())

    storage_handler = ElasticsearchStorageHandler(es_client=es_client, root_index=env.elastic_root_index)

    storage_handler.write_item(file)

    monkeypatch.setattr(app_module, "get_embeddings", lambda _: FakeEmbeddings(size=3072))
    async with TestRedisBroker(broker) as br, TestApp(app):
        await br.publish(file, list=env.ingest_queue_name)
        storage_handler.refresh()

        if status == ProcessingStatusEnum.complete:
            chunks = storage_handler.get_file_chunks(file.uuid, file.creator_user_uuid)
            assert len(chunks) > 0
        storage_handler.refresh()
        file_status = storage_handler.get_file_status(file.uuid, file.creator_user_uuid)
        assert file_status.processing_status == status, file_status.processing_status
