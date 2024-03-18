import json
import logging

from model_db import SentenceTransformerDB
from redbox.models import File, ProcessingStatusEnum, Settings
from redbox.parsing.file_chunker import FileChunker
from redbox.storage.elasticsearch import ElasticsearchStorageHandler
from workers.queue import Queue

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()

env = Settings()


class FileIngestor:
    def __init__(
        self,
        raw_file_source,
        chunker: FileChunker,
        file_destination: ElasticsearchStorageHandler,
        queue: Queue
    ):
        self.raw_file_source = raw_file_source
        self.chunker = chunker
        self.file_destination = file_destination
        self.queue = queue

    def ingest_file(self, file: File):
        """
        1. Gets up file from s3
        2. Chunks file
        3. Puts chunks to ES
        4. Acknowledges message
        5. Puts chunk on embed-queue
        """

        logging.info(f"Ingesting file: {file}")

        authenticated_s3_url = self.raw_file_source.generate_presigned_url(
            "get_object",
            Params={"Bucket": env.bucket_name, "Key": file.name},
            ExpiresIn=180,
        )

        file.processing_status = ProcessingStatusEnum.chunking
        self.file_destination.update_item(file.uuid, file)

        chunks = self.chunker.chunk_file(
            file=file,
            file_url=authenticated_s3_url,
            creator_user_uuid=file.creator_user_uuid,
        )

        logging.info(f"Writing {len(chunks)} chunks to storage for file uuid: {file.uuid}")

        items = self.file_destination.write_items(chunks)
        logging.info(f"written {len(items)} chunks to elasticsearch")

        self.queue.send_message_to_queue(chunks, env.embed_queue_name)
        return items

    def callback(self, ch, method, _properties, body):
        logging.info("Received message")
        file = File(**json.loads(body))
        logging.info(f"Starting ingest for file (uuid: {file.uuid}, name: {file.name})")
        try:
            self.ingest_file(file)
            logging.info("ingestion complete")
        except Exception as e:
            logging.error(f"ingestion failed: {e}")
        finally:
            ch.basic_ack(delivery_tag=method.delivery_tag)


def run():
    """
    0. Listens to queue
    1. On Receipt of a File metadata message from queue
    2. Callbacks to ingest_file
    """

    # ====== Loading embedding model ======

    models = SentenceTransformerDB()

    models.init_from_disk()

    # === Object Store ===

    s3 = env.s3_client()

    # === Queues ===

    ingest_queue = Queue(env.ingest_queue_name)
    embed_queue = Queue(env.embed_queue_name)

    # === Storage ===

    es = env.elasticsearch_client()

    storage_handler = ElasticsearchStorageHandler(es_client=es, root_index="redbox-data")
    chunker = FileChunker(embedding_model=models[env.embedding_model])

    file_ingestor = FileIngestor(s3, chunker, storage_handler, embed_queue)

    ingest_queue.setup_listener(queue_name=env.ingest_queue_name, callback=file_ingestor.callback)


if __name__ == "__main__":
    run()
