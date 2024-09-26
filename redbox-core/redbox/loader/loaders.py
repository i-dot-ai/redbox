from collections.abc import Iterator
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING

import requests

# import textract
import tiktoken
from langchain_core.documents import Document
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pymediainfo import MediaInfo

from redbox.chains.components import get_chat_llm
from redbox.loader.base import BaseRedboxFileLoader
from redbox.models.chain import AISettings
from redbox.models.file import ChunkMetadata, ChunkResolution
from redbox.models.settings import Settings

encoding = tiktoken.get_encoding("cl100k_base")

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client
else:
    S3Client = object


class UnstructuredChunkLoader(BaseRedboxFileLoader):
    """Load, partition and chunk a document using local unstructured library"""

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

    def detect_encoding_and_extract_text(
        file_name: str, file_bytes: BytesIO, tokens: int
    ) -> str:
        """Detect encoding and extract first n tokens from any document type."""
        encoding = tiktoken.encoding_for_model("gpt-4")
        file_path = Path(file_name)

        try:
            with NamedTemporaryFile(
                prefix=file_path.stem, suffix=file_path.suffix, delete=True, mode="wb"
            ) as temp_file:
                temp_file.write(file_bytes.getvalue())
                temp_file.flush()
            #     text = textract.process(temp_file.name).decode("utf-8")

            # first_n = encoding.encode(text)[:tokens]

            # return encoding.decode(first_n)
            return True
        except Exception as e:
            raise ValueError(f"An error occurred while extracting text: {str(e)}")

    def extract_hardcoded_metadata(
        file_name: str, file_bytes: BytesIO
    ) -> dict[str, str]:
        file_path = Path(file_name)

        try:
            with NamedTemporaryFile(
                prefix=file_path.stem, suffix=file_path.suffix, delete=True, mode="wb"
            ) as temp_file:
                temp_file.write(file_bytes.getvalue())
                temp_file.flush()
                media_info = MediaInfo.parse(temp_file.name)
                metadata = {}

                for track in media_info.tracks:
                    if track.track_type == "General":
                        metadata["title"] = (
                            track.title if track.title else file_path.name
                        )
                        metadata["creator"] = (
                            track.performer
                            if track.performer
                            else track.album_performer
                        )
                        metadata["subject"] = track.track_type
                        metadata["description"] = track.comment
                        metadata["publisher"] = track.publisher
                        metadata["date"] = track.recorded_date
                        metadata["language"] = track.language
                        metadata["format"] = track.format

                return metadata
        except Exception as e:
            raise ValueError(f"An error occurred while extracting text: {str(e)}")

    def get_metadata(self) -> dict[str, Any]:
        LLM = get_chat_llm(env=self.env, ai_settings=AISettings)
        metadata_chain = (
            ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        "You are an SEO specialist that must optimise the metadata of a document to make it as discoverable as possible. You are about to be given the first 1_000 tokens of a document and any hard-coded file metadata that can be recovered from it. Create SEO-optimised metadata for this document in the structured data markup (JSON-LD) standard. You must include at least the 'name', 'description' and 'keywords' properties but otherwise use your expertise to make the document as easy to search for as possible. Return only the JSON-LD: \n\n",
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
            | LLM
            | JsonOutputParser()
        )

        return metadata_chain.invoke(
            {
                "page_content": self.detect_encoding_and_extract_text(
                    file_name=self.file_name, file_bytes=self.file_bytes, tokens=1_000
                ),
                "metadata": self.extract_hardcoded_metadata(
                    file_name=self.file_name,
                    file_bytes=self.file_bytes,
                ),
            }
        )

    def coerce_to_string_list(input_data: str | list[Any]) -> list[str]:
        if isinstance(input_data, str):
            return [item.strip() for item in input_data.split(",")]
        elif isinstance(input_data, list):
            return [str(i) for i in input_data]
        else:
            raise ValueError("Input must be either a list or a string.")

    def lazy_load(self, file_name: str, file_bytes: BytesIO) -> Iterator[Document]:
        """A lazy loader that reads a file line by line.

        When you're implementing lazy load methods, you should use a generator
        to yield documents one by one.
        """
        metadata = self.get_metadata()

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
                    name=metadata.get("name", self.file_name),
                    description=metadata.get("description", "None"),
                    keywords=self.coerce_to_string_list(metadata.get("keywords", [])),
                    # prepositions=preposition_chain.invoke({"page_content": raw_chunk["text"]}),
                ).model_dump(),
            )
