import json
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

from redbox.chains.components import get_chat_llm
from redbox.models.file import ChunkResolution, UploadedFileMetadata
from redbox.models.settings import Settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

encoding = tiktoken.get_encoding("cl100k_base")

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client
else:
    S3Client = object


def get_first_n_tokens(chunks: list[dict] | None, n: int) -> str:
    """From a list of chunks, returns the first n tokens."""

    current_tokens = 0
    tokens = ""
    if not chunks:
        return tokens

    for chunk in chunks:
        current_tokens += len(encoding.encode(chunk["text"]))
        if current_tokens > n:
            return tokens
        tokens += chunk["text"]
    return tokens


class MetadataLoader:
    required_keys = {"name", "description", "keywords"}

    def __init__(self, env: Settings, s3_client: S3Client, file_name: str):
        self.env = env
        self.s3_client = s3_client
        self.llm = get_chat_llm(env.metadata_extraction_llm)
        self.file_name = file_name

    def _get_file_bytes(self, s3_client: S3Client, file_name: str) -> BytesIO:
        return s3_client.get_object(Bucket=self.env.bucket_name, Key=file_name)["Body"].read()

    def _chunking(self) -> Any:
        """
        Chunking data using local unstructured
        """
        file_bytes = self._get_file_bytes(s3_client=self.s3_client, file_name=self.file_name)
        url = f"http://{self.env.unstructured_host}:8000/general/v0/general"
        files = {
            "files": (self.file_name, file_bytes),
        }
        response = requests.post(
            url,
            files=files,
            data={
                "strategy": "fast",
                "chunking_strategy": "by_title",
                "max_characters": self.env.worker_ingest_max_chunk_size,
                "combine_under_n_chars": self.env.worker_ingest_min_chunk_size,
                "overlap": 0,
                "overlap_all": True,
            },
        )

        if response.status_code != 200:
            raise ValueError(response.text)

        return response.json()

    def extract_metadata(self) -> dict:
        """
        Extract metadata from first 1_000 chunks
        """

        elements = self._chunking()

        # Get first 1k tokens of processed document
        first_n = get_first_n_tokens(elements, 1_000)

        # Generate new metadata
        res = self.create_file_metadata(first_n)
        return {key: res.get(key) for key in self.required_keys}

    def create_file_metadata(self, page_content: str) -> dict[str, Any]:
        """Uses a sample of the document and any extracted metadata to generate further metadata."""
        metadata_chain = (
            ChatPromptTemplate.from_messages(
                [
                    self.env.metadata_prompt,
                    (
                        "user",
                        ("<document_sample>\n" "{page_content}" "</document_sample>"),
                    ),
                ]
            )
            | self.llm
            | JsonOutputParser()
        )

        try:
            return metadata_chain.invoke({"page_content": page_content})
        except ConnectionError as e:
            logger.warning(f"Retrying due to HTTPError {e}")
        except json.JSONDecodeError:
            # replace with fail safe metadata
            return None
        except Exception as e:
            raise Exception(f"Some error happened in metadata extraction. {e}")


def coerce_to_string_list(input_data: str | list[Any]) -> list[str]:
    if isinstance(input_data, str):
        return [item.strip() for item in input_data.split(",")]
    elif isinstance(input_data, list):
        return [str(i) for i in input_data]
    else:
        raise ValueError("Input must be either a list or a string.")


class UnstructuredChunkLoader:
    """
    Load, partition and chunk a document using local unstructured library.
    """

    def __init__(
        self,
        chunk_resolution: ChunkResolution,
        env: Settings,
        min_chunk_size: int,
        max_chunk_size: int,
        metadata: dict,
        overlap_chars: int = 0,
        overlap_all_chunks: bool = True,
    ):
        self.chunk_resolution = chunk_resolution
        self.env = env
        self._min_chunk_size = min_chunk_size
        self._max_chunk_size = max_chunk_size
        self._overlap_chars = overlap_chars
        self._overlap_all_chunks = overlap_all_chunks
        self.metadata = metadata

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

        # add metadata below
        for i, raw_chunk in enumerate(elements):
            yield Document(
                page_content=raw_chunk["text"],
                metadata=UploadedFileMetadata(
                    index=i,
                    uri=file_name,
                    page_number=raw_chunk["metadata"].get("page_number"),
                    created_datetime=datetime.now(UTC),
                    token_count=len(encoding.encode(raw_chunk["text"])),
                    chunk_resolution=self.chunk_resolution,
                    name=self.metadata.get("name", file_name),
                    description=self.metadata.get("description"),
                    keywords=coerce_to_string_list(self.metadata.get("keywords", [])),
                ).model_dump(),
            )
