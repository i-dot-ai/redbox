import asyncio

import pytest
from faststream.redis import TestApp, TestRedisBroker
from langchain_core.embeddings.fake import FakeEmbeddings

from redbox.models.file import File
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
        await asyncio.sleep(1)

        chunks = storage_handler.get_file_chunks(file.uuid, file.creator_user_uuid)
        assert len(chunks) > 0
