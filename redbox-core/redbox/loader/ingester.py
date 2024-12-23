import logging
from datetime import datetime
from io import BytesIO
from typing import TYPE_CHECKING

from redbox.loader.loaders import UnstructuredChunkLoader
from redbox.models.settings import get_settings
from redbox.models.file import ChunkResolution, UploadedFileMetadata, ChunkCreatorType

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client
else:
    S3Client = object

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()

env = get_settings()




def ingest_file(file_name: str) -> tuple[str, UploadedFileMetadata]:
    s3_client = env.s3_client()
    loader = UnstructuredChunkLoader(
        chunk_resolution=ChunkResolution.normal,
        env=env,
        min_chunk_size=env.worker_ingest_min_chunk_size,
        max_chunk_size=env.worker_ingest_max_chunk_size,
        overlap_chars=0,
    )

    file_bytes = s3_client.get_object(Bucket=env.bucket_name, Key=file_name)["Body"].read()
    documents =list(loader.lazy_load(file_name=file_name, file_bytes=BytesIO(file_bytes)))

    page_content = "\n".join(document.page_content for document in documents)
    token_count = sum(document.token_count for document in documents)
    metadata = UploadedFileMetadata(
        index=1,
        uri=file_name,
        page_number=1,
        token_count=token_count,
        chunk_resolution=ChunkCreatorType.user_uploaded_document,
        created_datetime=datetime.now(),
       name=file_name,
    )

    return page_content, metadata
