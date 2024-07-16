from collections.abc import Iterator
from datetime import UTC, datetime
from typing import IO, TYPE_CHECKING

import tiktoken
from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document
from unstructured.chunking.title import chunk_by_title
from unstructured.partition.auto import partition

from redbox.models.file import File, ChunkResolution, ChunkMetadata
from redbox.models.settings import Settings

encoding = tiktoken.get_encoding("cl100k_base")

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client
else:
    S3Client = object


class UnstructuredTitleLoader(BaseLoader):
    """Load, partition and chunk a document using local unstructured library"""

    def __init__(self, file: File, file_bytes: IO[bytes], env: Settings) -> None:
        """Initialize the loader with a file path.

        Args:
            file: The RedBox File to load
        """
        self.file = file
        self.file_bytes = file_bytes
        self.env = env

    def lazy_load(self) -> Iterator[Document]:  # <-- Does not take any arguments
        """A lazy loader that reads a file line by line.

        When you're implementing lazy load methods, you should use a generator
        to yield documents one by one.
        """
        elements = partition(file=self.file_bytes, strategy=self.env.partition_strategy)
        raw_chunks = chunk_by_title(
            elements=elements,
            combine_text_under_n_chars=self.env.worker_ingest_min_chunk_size,
            max_characters=self.env.worker_ingest_max_chunk_size,
        )

        for i, raw_chunk in enumerate(raw_chunks):
            yield Document(
                page_content=raw_chunk.text,
                metadata=ChunkMetadata(
                    parent_file_uuid=self.file.uuid,
                    creator_user_uuid=self.file.creator_user_uuid,
                    index=i,
                    page_number=raw_chunk.metadata.page_number,
                    created_datetime=datetime.now(UTC),
                    token_count=len(encoding.encode(raw_chunk.text)),
                    chunk_resolution=ChunkResolution.normal                    
                ).model_dump(),
            )
