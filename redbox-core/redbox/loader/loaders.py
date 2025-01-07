import logging
from datetime import datetime
from io import BytesIO
import requests
import tiktoken

from redbox.models.file import ChunkResolution, UploadedFileMetadata
from redbox.models.settings import Settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

encoding = tiktoken.get_encoding("cl100k_base")


class UnstructuredChunkLoader:
    """
    Load, partition and chunk a document using local unstructured library.
    """

    def __init__(
        self,
        chunk_resolution: ChunkResolution,
        env: Settings,
    ):
        self.chunk_resolution = chunk_resolution
        self.env = env

    def lazy_load(self, file_name: str, file_bytes: BytesIO) -> tuple[str, UploadedFileMetadata]:
        """A lazy loader that reads a file line by line.

        When you're implementing lazy load methods, you should use a generator
        to yield documents one by one.
        """
        url = f"http://{self.env.unstructured_host}:8000/general/v0/general"
        files = {
            "files": (file_name, file_bytes),
        }
        response = requests.post(
            url,
            files=files,
            data={
                "strategy": "fast",
                "chunking_strategy": "by_title",
            },
        )

        if response.status_code != 200:
            raise ValueError(response.text)

        elements = response.json()

        if not elements:
            raise ValueError("Unstructured failed to extract text for this file")

        # add metadata below
        page_content = "\n".join(raw_chunk["text"] for raw_chunk in elements)
        token_count = len(encoding.encode(page_content))

        metadata = UploadedFileMetadata(
            index=1,
            uri=file_name,
            page_number=1,
            token_count=token_count,
            created_datetime=datetime.now(),
            name=file_name,
        )
        return page_content, metadata
