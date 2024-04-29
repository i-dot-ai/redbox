from enum import Enum

from sentence_transformers import SentenceTransformer

from redbox.models.file import Chunk, File
from redbox.parsing.chunk_clustering import cluster_chunks
from redbox.parsing.chunkers import other_chunker


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


class FileChunker:
    """A class to wrap unstructured and generate compliant chunks from files"""

    def __init__(self, embedding_model: SentenceTransformer = None):
        self.supported_file_types = [content_type.value for content_type in ContentType]
        self.embedding_model = embedding_model

    def chunk_file(
        self,
        file: File,
        chunk_clustering: bool = True,
    ) -> list[Chunk]:
        """_summary_

        Args:
            file (File): The file to read, analyse layout and chunk.
            chunk_clustering (bool): Whether to merge small semantically similar chunks.
                Defaults to True.
        Raises:
            ValueError: Will raise when a file is not supported.

        Returns:
            List[Chunk]: The chunks generated from the given file.
        """
        chunks = other_chunker(file)

        if chunk_clustering:
            chunks = cluster_chunks(chunks, embedding_model=self.embedding_model)

        return chunks
