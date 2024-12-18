import logging
from collections.abc import Iterator
from datetime import UTC, datetime
from io import BytesIO
from typing import TYPE_CHECKING
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
import requests
import tiktoken
from langchain_core.documents import Document


from redbox.chains.components import get_chat_llm
from redbox.models.file import ChunkResolution, UploadedFileMetadata
from redbox.models.settings import Settings
from redbox.models.chain import GeneratedMetadata

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

encoding = tiktoken.get_encoding("cl100k_base")

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client
else:
    S3Client = object


class MetadataLoader:
    def __init__(self, env: Settings, s3_client: S3Client, file_name: str):
        self.env = env
        self.s3_client = s3_client
        self.llm = get_chat_llm(env.metadata_extraction_llm)
        self.file_name = file_name

    def _get_file_bytes(self, s3_client: S3Client, file_name: str) -> BytesIO:
        return s3_client.get_object(Bucket=self.env.bucket_name, Key=file_name)["Body"].read()

    def _chunking(self) -> list[dict]:
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

        return response.json() or []

    def extract_metadata(self) -> GeneratedMetadata:
        """
        Extract metadata from first 1_000 chunks
        """

        chunks = self._chunking()
        original_metadata = chunks[0]["metadata"] if chunks else {}
        first_thousand_words = "".join(chunk["text"] for chunk in chunks)[:10_000]

        try:
            metadata = self.create_file_metadata(first_thousand_words, original_metadata=original_metadata)
        except TypeError:
            metadata = GeneratedMetadata(name=original_metadata.get("filename"))
        return metadata

    def create_file_metadata(self, page_content: str, original_metadata: dict | None = None) -> GeneratedMetadata:
        """Uses a sample of the document and any extracted metadata to generate further metadata."""
        if not original_metadata:
            original_metadata = {}

        def trim(obj, max_length=1000):
            """original_metadata can be very long as it includes the original text"""
            if isinstance(obj, dict):
                return {k: trim(v, max_length) for k, v in obj.items()}
            if isinstance(obj, list):
                return [trim(v, max_length) for v in obj]
            if isinstance(obj, str):
                return obj[:max_length]
            return obj

        original_metadata = trim(original_metadata)

        parser = PydanticOutputParser(pydantic_object=GeneratedMetadata)
        metadata_prompt = PromptTemplate(
            template="".join(self.env.metadata_prompt)
            + "\n\n{format_instructions}\n\n{page_content}\n\n{original_metadata}",
            input_variables=["page_content"],
            partial_variables={
                "format_instructions": parser.get_format_instructions(),
                "original_metadata": original_metadata,
            },
        )
        metadata_chain = metadata_prompt | self.llm

        output = metadata_chain.invoke({"page_content": page_content})

        return parser.invoke(output)


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
                    name=self.metadata.name,
                    description=self.metadata.description,
                    keywords=self.metadata.keywords,
                ).model_dump(),
            )
