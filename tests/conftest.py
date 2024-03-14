import os
from typing import TypeVar, Generator

import pytest
from elasticsearch import Elasticsearch

from redbox.models import Settings

T = TypeVar("T")

YieldFixture = Generator[T, None, None]

env = Settings()


@pytest.fixture
def file_pdf_path() -> YieldFixture[str]:
    path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "data",
        "pdf",
        "Cabinet Office - Wikipedia.pdf",
    )
    yield path


@pytest.fixture
def es_client() -> YieldFixture[Elasticsearch]:
    es = Elasticsearch(
        hosts=[
            {
                "host": "localhost",
                "port": env.elastic_port,
                "scheme": env.elastic_scheme,
            }
        ],
        basic_auth=(env.elastic_user, env.elastic_password),
    )

    yield es
