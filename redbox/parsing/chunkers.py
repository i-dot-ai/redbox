from collections.abc import Sequence
from typing import TYPE_CHECKING

from unstructured.chunking.title import chunk_by_title
from unstructured.partition.auto import partition

from redbox.models import Chunk, File, Settings
from redbox.models.file import Metadata

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client
else:
    S3Client = object

env = Settings()


def other_chunker(file: File, s3_client: S3Client) -> Sequence[Chunk]:
    """The default unstructured chunker for Redbox. This chunker uses the unstructured partitioner and title chunker
    to split a file into chunks.

    Args:
        file (File): The file to be chunked from the Redbox backend.

    Returns:
        list[Chunk]: A list of chunks that have been created from the file.
    """
    authenticated_s3_url = s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": file.bucket, "Key": file.key},
        ExpiresIn=3600,
    )

    elements = partition(url=authenticated_s3_url, strategy=env.partition_strategy)
    raw_chunks = chunk_by_title(elements=elements)

    return [
        Chunk(
            parent_file_uuid=file.uuid,
            index=i,
            text=raw_chunk.text,
            metadata=Metadata(
                parent_doc_uuid=file.uuid,
                page_number=raw_chunk.metadata.page_number,
                languages=raw_chunk.metadata.languages,
                link_texts=raw_chunk.metadata.link_texts,
                link_urls=raw_chunk.metadata.link_urls,
                links=raw_chunk.metadata.links,
            ),
            creator_user_uuid=file.creator_user_uuid,
        )
        for i, raw_chunk in enumerate(raw_chunks)
    ]
