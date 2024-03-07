import json
import logging

from model_db import SentenceTransformerDB
from redbox.models import File, Settings
from redbox.parsing.file_chunker import FileChunker
from redbox.storage.elasticsearch import ElasticsearchStorageHandler

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()

env = Settings()


class FileIngestor:
    """
    0. listens to queue
    1. receives File message from queue
    2. not sure but either:
        picks up file from s3
        gets file obj directly from queue, but then why s3 ref?
    3. chunks file
    4. writes chunks to ES
    5. acknowledges message
    """

    def __init__(
        self,
        raw_file_source,
        chunker: FileChunker,
        chunked_file_destination: ElasticsearchStorageHandler,
    ):
        self.raw_file_source = raw_file_source
        self.chunker = chunker
        self.chunked_file_destination = chunked_file_destination

    def ingest_file(self, file: File):
        logging.info(f"Ingesting file: {file}")

        authenticated_s3_url = self.raw_file_source.generate_presigned_url(
            "get_object",
            Params={"Bucket": env.bucket_name, "Key": file.name},
            ExpiresIn=180,
        )

        chunks = self.chunker.chunk_file(
            file=file,
            file_url=authenticated_s3_url,
            creator_user_uuid=file.creator_user_uuid,
        )

        logging.info(
            f"Writing {len(chunks)} chunks to storage for file uuid: {file.uuid}"
        )

        return self.chunked_file_destination.write_items(chunks)

    def callback(self, ch, method, _properties, body):
        logging.info("Received message")
        file = File(**json.loads(body))
        logging.info(f"Starting ingest for file (uuid: {file.uuid}, name: {file.name})")
        try:
            files = self.ingest_file(file)
            logging.info(f"blah blah blah {files}")
        except Exception:
            logging.error("blah blah blah")
        finally:
            ch.basic_ack(delivery_tag=method.delivery_tag)


def run():
    # ====== Loading embedding model ======

    models = SentenceTransformerDB()

    models.init_from_disk()

    # === Object Store ===

    s3 = env.s3_client()

    # === Queues ===

    if env.queue == "rabbitmq":
        connection = env.blocking_connection()
        channel = connection.channel()
        channel.queue_declare(queue=env.ingest_queue_name, durable=True)
    elif env.queue == "sqs":
        _sqs = env.sqs_client()
        raise NotImplementedError("SQS is not yet implemented")
    else:
        raise ValueError("must use rabbitmq")

    # === Storage ===

    es = env.elasticsearch_client()

    storage_handler = ElasticsearchStorageHandler(
        es_client=es, root_index="redbox-data"
    )
    chunker = FileChunker(embedding_model=models[env.embedding_model])

    file_ingestor = FileIngestor(s3, chunker, storage_handler)

    channel.basic_consume(
        queue=env.ingest_queue_name, on_message_callback=file_ingestor.callback
    )
    channel.start_consuming()


if __name__ == "__main__":
    run()
