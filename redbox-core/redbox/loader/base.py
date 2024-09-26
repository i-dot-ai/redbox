from io import BytesIO

from langchain_core.document_loaders import BaseLoader

from redbox.models.settings import Settings


class BaseRedboxFileLoader(BaseLoader):
    def __init__(self, file_name: str, file_bytes: BytesIO, env: Settings) -> None:
        """Initialize the loader with a file path.

        Args:
            file: The Redbox File to load
        """
        self.file_name = file_name
        self.file_bytes = file_bytes
        self.env = env
