from typing import IO

from langchain_core.document_loaders import BaseLoader

from redbox.models.file import File  #
from redbox.models.settings import Settings


class BaseRedBoxFileLoader(BaseLoader):
    def __init__(self, file: File, file_bytes: IO[bytes], env: Settings) -> None:
        """Initialize the loader with a file path.

        Args:
            file: The RedBox File to load
        """
        self.file = file
        self.file_bytes = file_bytes
        self.env = env
