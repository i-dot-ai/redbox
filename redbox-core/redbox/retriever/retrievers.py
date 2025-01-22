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
        selected_files = set(query.request.s3_keys)
        permitted_files = set(query.request.permitted_s3_keys)

        if not selected_files <= permitted_files:
            logger.warning(
                "User has selected files they aren't permitted to access: \n"
                f"{", ".join(selected_files - permitted_files)}"
            )

        file_names = list(selected_files & permitted_files)

        files = self.file_manager.filter(original_file__in=file_names, text__isnull=False, metadata__isnull=False)

        return [Document(page_content=file.text, metadata=file.metadata) for file in files]


def retriever_runnable(retriever: BaseRetriever):
    def _run(state: RedboxState):
        state.documents = retriever.invoke(state)
        return state
    return _run