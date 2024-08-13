from __future__ import annotations

import hashlib
from enum import Enum, StrEnum
from uuid import UUID
import datetime

import tiktoken
from pydantic import BaseModel, Field, computed_field

from redbox.models.base import PersistableModel

encoding = tiktoken.get_encoding("cl100k_base")


class ProcessingStatusEnum(str, Enum):
    processing = "processing"
    embedding = "embedding"  # Used for processing while we transition to new statuses
    failed = "failed"
    complete = "complete"


class File(PersistableModel):
    """Reference to file stored on s3"""

    key: str = Field(description="file key")
    bucket: str = Field(description="s3 bucket")
    ingest_status: ProcessingStatusEnum | None = Field(
        description="Status of file ingest for files loaded by new worker", default=None
    )


class Link(BaseModel):
    text: str | None
    url: str
    start_index: int

    def __le__(self, other: Link):
        """required for sorted"""
        return self.start_index <= other.start_index

    def __hash__(self):
        return hash(self.text) ^ hash(self.url) ^ hash(self.start_index)


class Metadata(BaseModel):
    """this is a pydantic model for the unstructured Metadata class
    uncomment fields below and update merge as required"""

    parent_doc_uuid: UUID | None = Field(
        description="this field is not actually part of unstructured Metadata but is required by langchain",
        default=None,
    )

    # attached_to_filename: Optional[str] = None
    # category_depth: Optional[int] = None
    # coordinates: Optional[CoordinatesMetadata] = None
    # data_source: Optional[DataSourceMetadata] = None
    # detection_class_prob: Optional[float] = None
    # emphasized_text_contents: Optional[list[str]] = None
    # emphasized_text_tags: Optional[list[str]] = None
    # file_directory: Optional[str] = None
    # filename: Optional[str | pathlib.Path] = None
    # filetype: Optional[str] = None
    # header_footer_type: Optional[str] = None
    # image_path: Optional[str] = None
    # is_continuation: Optional[bool] = None
    languages: list[str] | None = None
    # last_modified: Optional[str] = None
    link_texts: list[str] | None = None
    link_urls: list[str] | None = None
    links: list[Link] | None = None
    # orig_elements: Optional[list[Element]] = None
    # page_name: Optional[str] = None
    page_number: int | list[int] | None = None
    # parent_id: Optional[UUID] = None
    # regex_metadata: Optional[dict[str, list[RegexMetadata]]] = None
    # section: Optional[str] = None
    # sent_from: Optional[list[str]] = None
    # sent_to: Optional[list[str]] = None
    # signature: Optional[str] = None
    # subject: Optional[str] = None
    # text_as_html: Optional[str] = None
    # url: Optional[str] = None

    @classmethod
    def merge(cls, left: Metadata | None, right: Metadata | None) -> Metadata | None:
        if not left:
            return right
        if not right:
            return left

        def listify(obj, field_name: str) -> list:
            field_value = getattr(obj, field_name, None)
            if isinstance(field_value, list):
                return field_value
            if field_value is None:
                return []
            return [field_value]

        def sorted_list_or_none(obj: list):
            return sorted(set(obj)) or None

        data = {
            field_name: sorted_list_or_none(listify(left, field_name) + listify(right, field_name))
            for field_name in cls.model_fields
        }

        if parent_doc_uuids := data.get("parent_doc_uuid"):
            parent_doc_uuids_without_none = [uuid for uuid in parent_doc_uuids if uuid]
            if len(parent_doc_uuids) > 1:
                message = "chunks do not have the same parent_doc_uuid"
                raise ValueError(message)
            data["parent_doc_uuid"] = parent_doc_uuids_without_none[0]
        return cls(**data)


class Chunk(PersistableModel):
    """Chunk of a File"""

    parent_file_uuid: UUID = Field(description="id of the original file which this text came from")
    index: int = Field(description="relative position of this chunk in the original file")
    text: str = Field(description="chunk of the original text")
    metadata: Metadata | dict | None = Field(
        description="subset of the unstructured Element.Metadata object", default=None
    )
    embedding: list[float] | None = Field(description="the vector representation of the text", default=None)

    @computed_field  # type: ignore[misc] # Remove if https://github.com/python/mypy/issues/1362 is fixed.
    @property  # Needed for type checking - see https://docs.pydantic.dev/2.0/usage/computed_fields/
    def text_hash(self) -> str:
        return hashlib.md5(self.text.encode(encoding="UTF-8", errors="strict"), usedforsecurity=False).hexdigest()

    @computed_field  # type: ignore[misc] # Remove if https://github.com/python/mypy/issues/1362 is fixed.
    @property  # Needed for type checking - see https://docs.pydantic.dev/2.0/usage/computed_fields/
    def token_count(self) -> int:
        return len(encoding.encode(self.text))


class ChunkStatus(BaseModel):
    """Status of a chunk of a file."""

    chunk_uuid: UUID
    embedded: bool


class FileStatus(BaseModel):
    """Status of a file."""

    file_uuid: UUID
    processing_status: ProcessingStatusEnum | None
    chunk_statuses: None = Field(default=None, description="deprecated, see processing_status")


class ChunkResolution(StrEnum):
    smallest = "smallest"
    small = "small"
    normal = "normal"
    large = "large"
    largest = "largest"


class ChunkMetadata(BaseModel):
    """
    Worker model for document metadata for new style chunks.
    This is the minimal metadata that all ingest chains provide and should not be used to map retrieved documents (as fields will be lost)
    """

    parent_file_uuid: UUID
    creator_user_uuid: UUID
    index: int
    file_name: str
    page_number: int | None = None
    created_datetime: datetime.datetime = datetime.datetime.now(datetime.UTC)
    token_count: int
    chunk_resolution: ChunkResolution = ChunkResolution.normal
