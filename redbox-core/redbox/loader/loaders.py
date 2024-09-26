from collections.abc import Iterator
from datetime import UTC, datetime
from io import BytesIO
from typing import TYPE_CHECKING

import requests
import tiktoken
from langchain_core.documents import Document

from redbox.models.file import ChunkMetadata, ChunkResolution
from redbox.models.settings import Settings

encoding = tiktoken.get_encoding("cl100k_base")

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client
else:
    S3Client = object


def get_first_n_tokens(chunks: list[dict], n: int) -> str:
    """From a list of chunks, returns the first n tokens."""
    current_tokens = 0
    tokens = ""
    for chunk in chunks:
        current_tokens += len(tiktoken.countit(chunk["text"]))
        if current_tokens > n:
            return tokens
        tokens += chunk["text"]
    return tokens


def get_doc_metadata() -> dict[str, Any]:
    """From either a list of chunks or the file_bytes, get some metadata.
    
    Either mediainfo or unstructured.
    """
    pass


from langchain_core.runnables import Runnable


class UnstructuredChunkLoader:
    """Load, partition and chunk a document using local unstructured library.
    
    Uses a metadata chain to extract metadata from the document where possible.
    """
    _get_metadata = (
        ChatPromptTemplate.from_messages([
            ("system", "You are an SEO specialist that must optimise the metadata of a document to make it as discoverable as possible. You are about to be given the first 1_000 tokens of a document and any hard-coded file metadata that can be recovered from it. Create SEO-optimised metadata for this document in the structured data markup (JSON-LD) standard. You must include at least the 'name', 'description' and 'keywords' properties but otherwise use your expertise to make the document as easy to search for as possible. Return only the JSON-LD: \n\n"),
            (
                "user", 
                (
                    "<metadata>\n"
                    "{metadata}\n"
                    "</metadata>\n\n"
                    "<document_sample>\n"
                    "{page_content}"
                    "</document_sample>"
                )
            ),
        ])
        | get_chat_llm()
        | JsonOutputParser()
    )

    def __init__(
        self,
        chunk_resolution: ChunkResolution,
        env: Settings,
        min_chunk_size: int,
        max_chunk_size: int,
        overlap_chars: int = 0,
        overlap_all_chunks: bool = True,
    ):
        self.chunk_resolution = chunk_resolution
        self.env = env
        self._min_chunk_size = min_chunk_size
        self._max_chunk_size = max_chunk_size
        self._overlap_chars = overlap_chars
        self._overlap_all_chunks = overlap_all_chunks

    def lazy_load(self, file_name: str, file_bytes: BytesIO) -> Iterator[Document]:
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
                "max_characters": self._max_chunk_size,
                "combine_under_n_chars": self._min_chunk_size,
                "overlap": self._overlap_chars,
                "overlap_all": self._overlap_all_chunks,
            },
        )

        if response.status_code != 200:
            raise ValueError(response.text)

        elements = response.json()

        if not elements:
            raise ValueError("Unstructured failed to extract text for this file")
        
        # Get first 1k tokens of processed document
        first_n = get_first_n_tokens(elements, 1_000)

        # Get whatever metadata we can from processed document
        metadata = get_doc_metadata()

        # Generate new metadata
        metdata = self._get_metadata.invoke(first_n, metadata)

        # add metadata below
        for i, raw_chunk in enumerate(elements):
            yield Document(
                page_content=raw_chunk["text"],
                metadata=ChunkMetadata(
                    index=i,
                    file_name=raw_chunk["metadata"].get("filename"),
                    page_number=raw_chunk["metadata"].get("page_number"),
                    created_datetime=datetime.now(UTC),
                    token_count=len(encoding.encode(raw_chunk["text"])),
                    chunk_resolution=self.chunk_resolution,
                ).model_dump(),
            )
