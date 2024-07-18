
import pytest
from faststream.redis import TestApp, TestRedisBroker
from langchain_core.embeddings.fake import FakeEmbeddings

from redbox.models.file import File, ProcessingStatusEnum
from redbox.storage import ElasticsearchStorageHandler
from worker.app import app, broker, env
from worker import app as app_module


@pytest.mark.asyncio()
async def test_ingest_file(es_client, file: File, monkeypatch):
    """
    Given that I have written a text File to s3
    When I call ingest_file
    I Expect to see this file to be:
    1. chunked
    2. written to Elasticsearch
    """

    storage_handler = ElasticsearchStorageHandler(es_client=es_client, root_index=env.elastic_root_index)

    storage_handler.write_item(file)

    monkeypatch.setattr(app_module, "get_embeddings", lambda _: FakeEmbeddings(size=3072))
    async with TestRedisBroker(broker) as br, TestApp(app):
        await br.publish(file, list=env.ingest_queue_name)
        storage_handler.refresh()

        chunks = storage_handler.get_file_chunks(file.uuid, file.creator_user_uuid)
        assert len(chunks) > 0


@pytest.mark.asyncio()
async def test_ingest_file_fail(es_client, bad_file: File, monkeypatch):
    """
    Given that I have written a corrupt file to s3
    When I call ingest_file
    I Expect:
     * 0 chunks to be produced
     * file-status to be `failed`
    """

    storage_handler = ElasticsearchStorageHandler(es_client=es_client, root_index=env.elastic_root_index)

    storage_handler.write_item(bad_file)

    monkeypatch.setattr(app_module, "get_embeddings", lambda _: FakeEmbeddings(size=3072))
    async with TestRedisBroker(broker) as br, TestApp(app):
        await br.publish(bad_file, list=env.ingest_queue_name)

    storage_handler.refresh()
    status = storage_handler.get_file_status(bad_file.uuid, bad_file.creator_user_uuid)
    assert status.processing_status == ProcessingStatusEnum.failed
