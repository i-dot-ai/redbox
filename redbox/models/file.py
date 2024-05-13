from __future__ import annotations

import hashlib
from enum import Enum
from typing import Optional
from uuid import UUID

import tiktoken
from pydantic import BaseModel, Field, computed_field

from redbox.models.base import PersistableModel

encoding = tiktoken.get_encoding("cl100k_base")


class ProcessingStatusEnum(str, Enum):
    chunking = "chunking"
    embedding = "embedding"
    complete = "complete"


class File(PersistableModel):
    """Reference to file stored on s3"""

    key: str = Field(description="file key")
    bucket: str = Field(description="s3 bucket")


class Link(BaseModel):
    text: Optional[str]
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

    parent_doc_uuid: Optional[UUID | None] = Field(
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
    languages: Optional[list[str]] = None
    # last_modified: Optional[str] = None
    link_texts: Optional[list[str]] = None
    link_urls: Optional[list[str]] = None
    links: Optional[list[Link]] = None
    # orig_elements: Optional[list[Element]] = None
    # page_name: Optional[str] = None
    page_number: Optional[int | list[int]] = None
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
    def merge(cls, left: Optional[Metadata], right: Optional[Metadata]) -> Optional[Metadata]:
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
            for field_name in cls.model_fields.keys()
        }

        if parent_doc_uuids := data.get("parent_doc_uuid"):
            parent_doc_uuids_without_none = [uuid for uuid in parent_doc_uuids if uuid]
            if len(parent_doc_uuids) > 1:
                raise ValueError("chunks do not have the same parent_doc_uuid")
            data["parent_doc_uuid"] = parent_doc_uuids_without_none[0]
        return cls(**data)


class Chunk(PersistableModel):
    """Chunk of a File"""

    parent_file_uuid: UUID = Field(description="id of the original file which this text came from")
    index: int = Field(description="relative position of this chunk in the original file")
    text: str = Field(description="chunk of the original text")
    metadata: Optional[Metadata] = Field(description="subset of the unstructured Element.Metadata object", default=None)
    embedding: Optional[list[float]] = Field(description="the vector representation of the text", default=None)

    @computed_field
    def text_hash(self) -> str:
        return hashlib.md5(self.text.encode(encoding="UTF-8", errors="strict"), usedforsecurity=False).hexdigest()

    @computed_field
    def token_count(self) -> int:
        return len(encoding.encode(self.text))


class ChunkStatus(BaseModel):
    """Status of a chunk of a file."""

    chunk_uuid: UUID
    embedded: bool


class FileStatus(BaseModel):
    """Status of a file."""

    file_uuid: UUID
    processing_status: ProcessingStatusEnum
    chunk_statuses: Optional[list[ChunkStatus]]


class FileExistsException(Exception):
    def __init__(self):
        super().__init__("Document with same name already exists. Please rename if you want to upload anyway.")
