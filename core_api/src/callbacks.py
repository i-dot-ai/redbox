from logging import Logger
from typing import Any

from langchain_core.callbacks.base import BaseCallbackHandler


class LoggerCallbackHandler(BaseCallbackHandler):
    def __init__(self, logger: Logger):
        self.logger: Logger = logger

    def on_chain_start(self, serialized: dict[str, Any], inputs: dict[str, Any], **kwargs: Any) -> None:  # noqa:ARG002
        """Run when chain starts running."""
        self.logger.info("Chain start: %s, inputs: %s", serialized, inputs)

    def on_chain_end(self, outputs: dict[str, Any], **kwargs: Any) -> None:  # noqa:ARG002
        """Run when chain ends running."""
        self.logger.info("Chain end: %s", outputs)

    def on_chain_error(self, error: Exception | KeyboardInterrupt, **kwargs: Any):  # noqa:ARG002
        """Run when chain errors."""
        self.logger.error("Chain error: %s", error)

    def on_text(self, text: str, **kwargs: Any) -> None:  # noqa:ARG002
        """Run on arbitrary text."""
        self.logger.info("Text: %s", text)
