from io import BytesIO
from typing import TYPE_CHECKING


from redbox.loader.loaders import UnstructuredChunkLoader
from redbox.models.settings import get_settings
from redbox.models.file import ChunkResolution, UploadedFileMetadata

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client
else:
    S3Client = object


env = get_settings()


def ingest_file(file_name: str) -> tuple[str, UploadedFileMetadata]:
    s3_client = env.s3_client()
    loader = UnstructuredChunkLoader(
        chunk_resolution=ChunkResolution.normal,
        env=env,
    )
    file_bytes = s3_client.get_object(Bucket=env.bucket_name, Key=file_name)["Body"].read()
    return loader.lazy_load(file_name=file_name, file_bytes=BytesIO(file_bytes))
