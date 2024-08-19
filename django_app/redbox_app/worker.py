import logging
from typing import TYPE_CHECKING

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


def ingest(
    file: File,
):
    from redbox_app.redbox_core.models import File as DJFile
    from redbox_app.redbox_core.models import StatusEnum

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
        new_ids = RunnableParallel({"normal": chunk_ingest_chain, "largest": large_chunk_ingest_chain}).invoke(file)
        DJFile.objects.filter(core_file_uuid=file.uuid).update(status=StatusEnum.complete)

        file.ingest_status = ProcessingStatusEnum.complete
        logging.info("File: %s %s chunks ingested", file, {k: len(v) for k, v in new_ids.items()})
    except Exception:
        logging.exception("Error while processing file [%s]", file)
        file.ingest_status = ProcessingStatusEnum.failed
        DJFile.objects.filter(core_file_uuid=file.uuid).update(status=StatusEnum.errored)

    finally:
        storage_handler.update_item(file)
