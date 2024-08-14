import logging
import os
from typing import TYPE_CHECKING

from celery import Celery, shared_task
from langchain_core.runnables import RunnableParallel
from langchain_elasticsearch.vectorstores import BM25RetrievalStrategy, ElasticsearchStore

from redbox.chains.components import get_embeddings
from redbox.chains.ingest import ingest_from_loader
from redbox.loader import UnstructuredLargeChunkLoader, UnstructuredTitleLoader
from redbox.models import File, ProcessingStatusEnum, Settings
from redbox.storage.elasticsearch import ElasticsearchStorageHandler

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client
else:
    S3Client = object

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()

env = Settings()


# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "redbox_app.settings")

app = Celery("redbox_app", broker="redis://redis:6379")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")


# Load task modules from all registered Django apps.
app.autodiscover_tasks()


def get_elasticsearch_store(es, es_index_name: str):
    return ElasticsearchStore(
        index_name=es_index_name,
        embedding=get_embeddings(env),
        es_connection=es,
        query_field="text",
        vector_query_field=env.embedding_document_field_name,
    )


def get_elasticsearch_store_without_embeddings(es, es_index_name: str):
    return ElasticsearchStore(
        index_name=es_index_name, es_connection=es, query_field="text", strategy=BM25RetrievalStrategy()
    )


def get_elasticsearch_storage_handler(es):
    return ElasticsearchStorageHandler(es, env.elastic_root_index)


@shared_task
async def ingest(
    file: File,
):
    logging.info("Ingesting file: %s", file)

    file.ingest_status = ProcessingStatusEnum.embedding
    es = env.elasticsearch_client()
    es_index_name = f"{env.elastic_root_index}-chunk"

    es.indices.create(index=es_index_name, ignore=[400])
    storage_handler = get_elasticsearch_storage_handler(es)

    chunk_ingest_chain = ingest_from_loader(
        document_loader_type=UnstructuredTitleLoader,
        s3_client=env.s3_client(),
        vectorstore=get_elasticsearch_store(es, es_index_name),
        env=env,
    )

    large_chunk_ingest_chain = ingest_from_loader(
        document_loader_type=UnstructuredLargeChunkLoader,
        s3_client=env.s3_client(),
        vectorstore=get_elasticsearch_store_without_embeddings(es, es_index_name),
        env=env,
    )
    storage_handler.update_item(file)

    try:
        new_ids = await RunnableParallel({"normal": chunk_ingest_chain, "largest": large_chunk_ingest_chain}).ainvoke(
            file
        )
        file.ingest_status = ProcessingStatusEnum.complete
        logging.info("File: %s %s chunks ingested", file, {k: len(v) for k, v in new_ids.items()})
    except Exception:
        logging.exception("Error while processing file [%s]", file)
        file.ingest_status = ProcessingStatusEnum.failed
    finally:
        storage_handler.update_item(file)
