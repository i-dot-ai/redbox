from io import BytesIO

from langchain_core.document_loaders import BaseLoader

from redbox.models.file import File
from redbox.models.settings import Settings


class BaseRedboxFileLoader(BaseLoader):
    def __init__(self, file: File, file_bytes: BytesIO, env: Settings) -> None:
        """Initialize the loader with a file path.

        Args:
            file: The Redbox File to load
        """
        self.file = file
        self.file_bytes = file_bytes
        self.env = env
