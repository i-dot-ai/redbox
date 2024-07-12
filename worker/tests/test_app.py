import asyncio

import pytest
from elasticsearch.helpers import scan
from faststream.redis import TestApp, TestRedisBroker
from langchain_core.embeddings.fake import FakeEmbeddings

from redbox.models.file import File
from redbox.storage import ElasticsearchStorageHandler
from worker.app import app, broker, env


@pytest.mark.asyncio()
async def test_ingest_file(file: File, session_mocker):
    """
    Given that I have written a text File to s3
    When I call ingest_file
    I Expect to see this file to be:
    1. chunked
    2. written to Elasticsearch
    """

    storage_handler = ElasticsearchStorageHandler(
        es_client=env.elasticsearch_client(), root_index=env.elastic_root_index
    )

    storage_handler.write_item(file)
    session_mocker.patch("redbox.models.Settings.get_embeddings", return_value=FakeEmbeddings(size=3072))
    async with TestRedisBroker(broker) as br, TestApp(app):
        await br.publish(file, list=env.ingest_queue_name)
        await asyncio.sleep(1)
        chunks = list(
            scan(
                client=env.elasticsearch_client(),
                index=f"{env.elastic_root_index}-chunk",
                query={
                    "query": {
                        "bool": {
                            "must": [
                                {
                                    "term": {
                                        "metadata.parent_file_uuid.keyword": str(file.uuid),
                                    }
                                },
                                {
                                    "term": {
                                        "metadata.creator_user_uuid.keyword": str(file.creator_user_uuid),
                                    }
                                },
                            ]
                        }
                    }
                },
            )
        )
        assert len(chunks) > 0
