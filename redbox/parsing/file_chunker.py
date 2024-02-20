from redbox.models.file import Chunk, File
from redbox.parsing.chunk_clustering import cluster_chunks
from redbox.parsing.chunkers import other_chunker


class FileChunker:
    """A class to wrap unstructured and generate compliant chunks from files"""

    def __init__(self):
        pass

    def chunk_file(
        self,
        file: File,
        file_url: str,
        chunk_clustering: bool = True,
        creator_user_uuid="dev",
    ) -> list[Chunk]:
        """_summary_

        Args:
            file (File): The file to read, analyse layout and chunk.
            file_url (str): The authenticated url of the file to fetch, analyse layout and chunk.
            chunk_clustering (bool): Whether to merge small semantically similar chunks.
                Defaults to True.
        Raises:
            ValueError: Will raise when a file is not supported.

        Returns:
            List[Chunk]: The chunks generated from the given file.
        """
        chunks = other_chunker(file, file_url, creator_user_uuid=creator_user_uuid)

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
