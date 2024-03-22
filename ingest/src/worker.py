import logging

from fast_depends import Depends
from faststream import FastStream
from faststream.rabbit import RabbitBroker, RabbitQueue

from redbox.model_db import SentenceTransformerDB
from redbox.models import EmbedQueueItem, File, ProcessingStatusEnum, Settings
from redbox.parsing.file_chunker import FileChunker
from redbox.storage.elasticsearch import ElasticsearchStorageHandler

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()

env = Settings()


def get_s3():
    return env.s3_client()


def get_storage() -> ElasticsearchStorageHandler:
    es = env.elasticsearch_client()
    storage_handler = ElasticsearchStorageHandler(es_client=es, root_index="redbox-data")
    return storage_handler


def get_chunker() -> FileChunker:
    models = SentenceTransformerDB()
    chunker = FileChunker(embedding_model=models[env.embedding_model])
    return chunker


broker = RabbitBroker(f"amqp://{env.rabbitmq_user}:{env.rabbitmq_password}@{env.rabbitmq_host}:{env.rabbitmq_port}/")
app = FastStream(broker)

ingest_channel = RabbitQueue(name=env.ingest_queue_name, durable=True)

embed_channel = RabbitQueue(name=env.embed_queue_name, durable=True)


@broker.subscriber(queue=ingest_channel)
def ingest(
    file: File,
    s3_client=Depends(get_s3),
    elasticsearch_storage_handler: ElasticsearchStorageHandler = Depends(get_storage),
    chunker: FileChunker = Depends(get_chunker),
):
    """
    1. Chunks file
    2. Puts chunks to ES
    3. Acknowledges message
    4. Puts chunk on embed-queue
    """

    logging.info(f"Ingesting file: {file}")

    authenticated_s3_url = s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": env.bucket_name, "Key": file.name},
        ExpiresIn=180,
    )

    file.processing_status = ProcessingStatusEnum.chunking
    elasticsearch_storage_handler.update_item(file.uuid, file)

    chunks = chunker.chunk_file(
        file=file,
        file_url=authenticated_s3_url,
        creator_user_uuid=file.creator_user_uuid,
    )

    logging.info(f"Writing {len(chunks)} chunks to storage for file uuid: {file.uuid}")

    items = elasticsearch_storage_handler.write_items(chunks)
    logging.info(f"written {len(items)} chunks to elasticsearch")

    for chunk in chunks:
        queue_item = EmbedQueueItem(model=env.embedding_model, chunk_uuid=chunk.uuid)
        logging.info(f"Writing chunk to storage for chunk uuid: {chunk.uuid}")
        broker.publish(
            queue_item,
            queue=embed_channel,
            exchange="redbox-core-exchange",
        )
    return items
