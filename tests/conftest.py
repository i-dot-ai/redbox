import os

from elasticsearch import Elasticsearch

from redbox.models import Settings
from redbox.storage.elasticsearch import ElasticsearchStorageHandler

import pytest

env = Settings(postgres_password="", django_secret_key="")


@pytest.fixture
def file_pdf_path():
    path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "data",
        "pdf",
        "Cabinet Office - Wikipedia.pdf",
    )
    yield path


@pytest.fixture
def es_client():
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


@pytest.fixture
def elasticsearch_storage_handler(es_client):
    yield ElasticsearchStorageHandler(es_client)
