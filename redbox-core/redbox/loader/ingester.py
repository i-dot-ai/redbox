import logging
from typing import TYPE_CHECKING

from langchain_core.runnables import RunnableParallel
from langchain_elasticsearch.vectorstores import BM25Strategy, ElasticsearchStore

from redbox.chains.components import get_embeddings
from redbox.chains.ingest import ingest_from_loader
from redbox.loader.loaders import MetadataLoader, UnstructuredChunkLoader
from redbox.models.settings import get_settings
from redbox.models.file import ChunkResolution

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client
else:
    S3Client = object

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()

env = get_settings()
alias = env.elastic_chunk_alias


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
        index_name=es_index_name,
        es_connection=es,
        query_field="text",
        strategy=BM25Strategy(),
    )


def create_alias(alias: str):
    es = env.elasticsearch_client()

    chunk_index_name = alias[:-8]  # removes -current

    es.options(ignore_status=[400]).indices.create(index=chunk_index_name)
    es.indices.put_alias(index=chunk_index_name, name=alias)


def ingest_file(file_name: str, es_index_name: str = alias) -> str | None:
    logging.info("Ingesting file: %s", file_name)

    es = env.elasticsearch_client()

    if es_index_name == alias:
        if not es.indices.exists_alias(name=alias):
            print("The alias does not exist")
            print(alias)
            print(es.indices.exists_alias(name=alias))
            create_alias(alias)
    else:
        es.options(ignore_status=[400]).indices.create(index=es_index_name)

    # Extract metadata
    metadata_loader = MetadataLoader(env=env, s3_client=env.s3_client(), file_name=file_name)
    metadata = metadata_loader.extract_metadata()

    chunk_ingest_chain = ingest_from_loader(
        loader=UnstructuredChunkLoader(
            chunk_resolution=ChunkResolution.normal,
            env=env,
            min_chunk_size=env.worker_ingest_min_chunk_size,
            max_chunk_size=env.worker_ingest_max_chunk_size,
            overlap_chars=0,
            metadata=metadata,
        ),
        s3_client=env.s3_client(),
        vectorstore=get_elasticsearch_store(es, es_index_name),
        env=env,
    )

    large_chunk_ingest_chain = ingest_from_loader(
        loader=UnstructuredChunkLoader(
            chunk_resolution=ChunkResolution.largest,
            env=env,
            min_chunk_size=env.worker_ingest_largest_chunk_size,
            max_chunk_size=env.worker_ingest_largest_chunk_size,
            overlap_chars=env.worker_ingest_largest_chunk_overlap,
            metadata=metadata,
        ),
        s3_client=env.s3_client(),
        vectorstore=get_elasticsearch_store_without_embeddings(es, es_index_name),
        env=env,
    )

    try:
        new_ids = RunnableParallel({"normal": chunk_ingest_chain, "largest": large_chunk_ingest_chain}).invoke(
            file_name
        )
        logging.info(
            "File: %s %s chunks ingested",
            file_name,
            {k: len(v) for k, v in new_ids.items()},
        )
    except Exception as e:
        logging.exception("Error while processing file [%s]", file_name)
        return f"{type(e)}: {e.args[0]}"
