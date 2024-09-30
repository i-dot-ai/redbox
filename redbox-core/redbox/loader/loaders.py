import logging
from collections.abc import Iterator
from datetime import UTC, datetime
from io import BytesIO
from typing import TYPE_CHECKING, Any

import requests
import tiktoken
from langchain_core.documents import Document
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from requests.exceptions import HTTPError

from redbox.chains.components import get_chat_llm
from redbox.models.chain import AISettings
from redbox.models.file import ChunkMetadata, ChunkResolution
from redbox.models.settings import Settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

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
        current_tokens += len(encoding.encode(chunk["text"]))
        if current_tokens > n:
            return tokens
        tokens += chunk["text"]
    return tokens


def get_doc_metadata(
    chunks: list[dict], n: int, ignore: list[str] = None
) -> dict[str, Any]:
    """
    Use the first n chunks to get metadata using unstructured.
    Metadata keys in the ignore list will be excluded from the result.
    """
    metadata = {}
    for i, chunk in enumerate(chunks):
        if i > n:
            return metadata
        metadata = merge_unstructured_metadata(metadata, chunk["metadata"], ignore)
    return metadata


def merge_unstructured_metadata(x: dict, y: dict, ignore: list[str] = None) -> dict:
    """
    Combine 2 dicts without deleting any elements. If the key is present in both,
    combine values into a list. If value is in a list, extend with unique values.
    Keys in the ignore list will be excluded from the result.
    """
    if ignore is None:
        ignore = []

    combined = {}

    ignore_set = set(ignore)

    for key in set(x) | set(y):
        if key in ignore_set:
            continue

        if key in x and key in y:
            if isinstance(x[key], list) or isinstance(y[key], list):
                combined[key] = list(
                    set(x[key] + (y[key] if isinstance(y[key], list) else [y[key]]))
                )
            else:
                combined[key] = [x[key], y[key]]
        elif key in x:
            combined[key] = x[key]
        else:
            combined[key] = y[key]

    return combined


def coerce_to_string_list(input_data: str | list[Any]) -> list[str]:
    if isinstance(input_data, str):
        return [item.strip() for item in input_data.split(",")]
    elif isinstance(input_data, list):
        return [str(i) for i in input_data]
    else:
        raise ValueError("Input must be either a list or a string.")


class UnstructuredChunkLoader:
    """Load, partition and chunk a document using local unstructured library.

    Uses a metadata chain to extract metadata from the document where possible.
    """

    llm = None

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
        self.llm = get_chat_llm(self.env, AISettings())

    def create_file_metadata(
        self, page_content: str, metadata: dict[str, Any]
    ) -> dict[str, Any]:
        """Uses a sample of the document and any extracted metadata to generate further metadata."""
        metadata_chain = (
            ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        "You are an SEO specialist that must optimise the metadata of a document "
                        "to make it as discoverable as possible. You are about to be given the first "
                        "1_000 tokens of a document and any hard-coded file metadata that can be "
                        "recovered from it. Create SEO-optimised metadata for this document in the "
                        "structured data markup (JSON-LD) standard. You must include at least "
                        "the 'name', 'description' and 'keywords' properties but otherwise use your "
                        "expertise to make the document as easy to search for as possible. "
                        "Return only the JSON-LD: \n\n",
                    ),
                    (
                        "user",
                        (
                            "<metadata>\n"
                            "{metadata}\n"
                            "</metadata>\n\n"
                            "<document_sample>\n"
                            "{page_content}"
                            "</document_sample>"
                        ),
                    ),
                ]
            )
            | self.llm
            | JsonOutputParser().with_retry(stop_after_attempt=3)
        )

        try:
            return metadata_chain.invoke(
                {"page_content": page_content, "metadata": metadata}
            )
        except HTTPError as e:
            logger.warning(f"Retrying due to HTTPError {e.response.status_code}")

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
        metadata = get_doc_metadata(chunks=elements, n=3, ignore=None)

        # Generate new metadata
        metadata = self.create_file_metadata(first_n, metadata)

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
                    name=metadata.get("name", file_name),
                    description=metadata.get("description", "None"),
                    keywords=coerce_to_string_list(metadata.get("keywords", [])),
                ).model_dump(),
            )
