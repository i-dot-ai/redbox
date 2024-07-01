from collections.abc import Sequence
from enum import Enum
from typing import TYPE_CHECKING

from sentence_transformers import SentenceTransformer  # type: ignore

from redbox.models.file import Chunk, File
from redbox.parsing.chunk_clustering import cluster_chunks
from redbox.parsing.chunkers import other_chunker

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client
else:
    S3Client = object


class ContentType(str, Enum):
    EML = ".eml"
    HTML = ".html"
    HTM = ".htm"
    JSON = ".json"
    MD = ".md"
    MSG = ".msg"
    RST = ".rst"
    RTF = ".rtf"
    TXT = ".txt"
    XML = ".xml"
    JPEG = ".jpeg"  # Must have tesseract installed
    PNG = ".png"  # Must have tesseract installed
    CSV = ".csv"
    DOC = ".doc"
    DOCX = ".docx"
    EPUB = ".epub"
    ODT = ".odt"
    PDF = ".pdf"
    PPT = ".ppt"
    PPTX = ".pptx"
    TSV = ".tsv"
    XLSX = ".xlsx"


def chunk_file(
    file: File,
    s3_client: S3Client,
    embedding_model: SentenceTransformer | None = None,
    desired_chunk_size: int = 300,
) -> Sequence[Chunk]:
    """
    Args:
        file (File): The file to read, analyse layout and chunk.
        embedding_model (SentenceTransformer): The model to use
            to merge small semantically similar chunks, if not
            specified, not clustering will happen.
    Raises:
        ValueError: Will raise when a file is not supported.

    Returns:
        Sequence[Chunk]: The chunks generated from the given file.
    """
    chunks = other_chunker(file=file, s3_client=s3_client)

    if embedding_model is not None:
        chunks = cluster_chunks(chunks, embedding_model=embedding_model, desired_chunk_size=desired_chunk_size)

    return chunks
