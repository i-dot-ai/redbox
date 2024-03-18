from typing import TypeVar, Generator

import pytest
from pika import BlockingConnection
from pika.adapters.blocking_connection import BlockingChannel

from ingest.src.app import env

T = TypeVar("T")

YieldFixture = Generator[T, None, None]


@pytest.fixture
def rabbitmq_connection() -> YieldFixture[BlockingConnection]:
    connection = env.blocking_connection()
    yield connection
    connection.close()


@pytest.fixture
def rabbitmq_channel(rabbitmq_connection: BlockingConnection) -> YieldFixture[BlockingChannel]:
    channel = rabbitmq_connection.channel()
    channel.queue_declare(
        queue=env.embed_queue_name,
        durable=True,
    )
    yield channel
    channel.close()
