from typing import TYPE_CHECKING
import logging
from io import BytesIO

from langchain.vectorstores import VectorStore
from langchain_core.documents.base import Document
from langchain_core.runnables import RunnableLambda, chain

from redbox.models.settings import Settings
from redbox.models.file import File


if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client
else:
    S3Client = object

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


@chain
def log_chunks(chunks: list[Document]):
    log.info("Processing %s chunks", len(chunks))
    return chunks


def document_loader(document_loader_type, s3_client: S3Client, env: Settings):
    @chain
    def wrapped(file: File):
        file_raw = BytesIO()
        s3_client.download_fileobj(Bucket=file.bucket, Key=file.key, Fileobj=file_raw)
        file_raw.seek(0)
        return document_loader_type(file=file, file_bytes=file_raw, env=env).lazy_load()

    return wrapped


def ingest_from_loader(document_loader_type: type, s3_client: S3Client, vectorstore: VectorStore, env: Settings):
    return (
        document_loader(document_loader_type=document_loader_type, s3_client=s3_client, env=env)
        | RunnableLambda(list)
        | log_chunks
        | RunnableLambda(vectorstore.aadd_documents)  # type: ignore[arg-type]
    )
