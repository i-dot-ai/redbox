from typing import List

from redbox.models.file import Chunk, File
from redbox.parsing.chunk_clustering import cluster_chunks
from redbox.parsing.chunkers import email_chunker, other_chunker


class FileChunker:
    """A class to wrap unstructured and generate compliant chunks from files"""

    def __init__(self):
        self.supported_file_types = {
            ".eml": email_chunker,
            ".html": other_chunker,
            ".json": other_chunker,
            ".md": other_chunker,
            ".msg": other_chunker,
            ".rst": other_chunker,
            ".rtf": other_chunker,
            ".txt": other_chunker,
            ".xml": other_chunker,
            # ".jpeg", # Must have tesseract installed
            # ".png", # Must have tesseract installed
            ".csv": other_chunker,
            ".doc": other_chunker,
            ".docx": other_chunker,
            ".epub": other_chunker,
            ".odt": other_chunker,
            ".pdf": other_chunker,
            ".ppt": other_chunker,
            ".pptx": other_chunker,
            ".tsv": other_chunker,
            ".xlsx": other_chunker,
        }

    def chunk_file(
        self, file: File, chunk_clustering: bool = True, creator_user_uuid="dev"
    ) -> List[Chunk]:
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
        # Check we can process
        if file.type not in list(self.supported_file_types.keys()):
            raise ValueError(f"File type {file.type} of {file.name} is not supported")

        chunker = self.supported_file_types.get(file.type)
        chunks = chunker(file, creator_user_uuid=creator_user_uuid)

        if chunk_clustering:
            chunks = cluster_chunks(chunks)

        # Ensure page numbers are a list for schema compliance
        for chunk in chunks:
            if "page_number" in chunk.metadata:
                if isinstance(chunk.metadata["page_number"], int):
                    chunk.metadata["page_numbers"] = [chunk.metadata["page_number"]]
                elif isinstance(chunk.metadata["page_number"], list):
                    chunk.metadata["page_numbers"] = chunk.metadata["page_number"]
                del chunk.metadata["page_number"]

        return chunks

    def chunk_files(self, files: List[File]) -> List[List[Chunk]]:
        """A bulk function for chunking files.

        Args:
            files (List[File]): List of files to chunk

        Returns:
            List[List[Chunk]]: A list of lists for all the chunks extracted from each file.
        """
        return [self.chunk_file(file=file) for file in files]
