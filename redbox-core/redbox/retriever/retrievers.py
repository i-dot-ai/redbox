from logging import getLogger

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from redbox.models.chain import RedboxState
from typing import Any

logger = getLogger(__name__)


class DjangoFileRetriever(BaseRetriever):
    file_manager: Any = None

    def _get_relevant_documents(
        self, query: RedboxState, *, run_manager: CallbackManagerForRetrieverRun
    ) -> list[Document]:
        files = self.file_manager.filter(
            original_file__in=query.request.s3_keys, text__isnull=False, metadata__isnull=False
        )

        return [
            Document(page_content=file.text, metadata={"token_count": file.token_count, "uri": file.url})
            for file in files
        ]
