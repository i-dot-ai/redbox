import pytest
from faststream.redis import TestRedisBroker


from ingester.src.worker import router
from redbox.models import Settings
from redbox.storage import ElasticsearchStorageHandler

env = Settings()


@pytest.mark.asyncio
async def test_ingest_file(s3_client, es_client, embedding_model, file):
    """
    Given that I have written a text File to s3
    When I call ingest_file
    I Expect to see this file to be:
    1. chunked
    2. written to Elasticsearch
    """

    storage_handler = ElasticsearchStorageHandler(es_client=es_client, root_index="redbox-data")

    storage_handler.write_item(file)

    async with TestRedisBroker(router.broker) as br:
        await br.publish(file, channel=env.ingest_queue_name)

        file = storage_handler.read_item(
            item_uuid=file.uuid,
            model_type="File",
        )

        assert file is not None


def test_get_health(app_client):
    """
    Given that the app is running
    When I call /health
    I Expect to see the docs
    """
    response = app_client.get("/health")
    assert response.status_code == 200
