from collections.abc import Callable
from dataclasses import dataclass, field
import datetime
import logging
from typing import Generator
from uuid import uuid4

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from redbox.models.chain import RedboxQuery
from redbox.models.chat import ChatRoute
from redbox.models.file import ChunkMetadata, ChunkResolution
from redbox.models.graph import RedboxActivityEvent

log = logging.getLogger()


def generate_docs(
    s3_key: str = "test_data.pdf",
    page_numbers: list[int] = [1, 2, 3, 4],
    total_tokens: int = 6000,
    number_of_docs: int = 10,
    chunk_resolution=ChunkResolution.normal,
) -> Generator[Document, None, None]:
    """Generates a list of documents as if retrieved from a real retriever.

    For this reason, adds extra data beyond ChunkMetadata, mimicing
    redbox.retriever.retrievers.hit_to_doc().
    """
    for i in range(number_of_docs):
        core_metadata = ChunkMetadata(
            index=i,
            file_name=s3_key,
            page_number=page_numbers[int(i / number_of_docs) * len(page_numbers)],
            created_datetime=datetime.datetime.now(datetime.UTC),
            token_count=int(total_tokens / number_of_docs),
            chunk_resolution=chunk_resolution,
        ).model_dump()

        extra_metadata = {
            "score": 1,
            "uuid": uuid4(),
        }

        yield Document(
            page_content=f"Document {i} text",
            metadata=core_metadata | extra_metadata,
        )


@dataclass
class RedboxTestData:
    number_of_docs: int
    tokens_in_all_docs: int
    chunk_resolution: ChunkResolution = ChunkResolution.largest
    expected_llm_response: list[str] = field(default_factory=list)
    expected_route: ChatRoute | None = None
    expected_activity_events: Callable[[list[RedboxActivityEvent]], bool] = field(
        default=lambda _: True
    )  # Function to check activity events are as expected
    s3_keys: str | None = None


class RedboxChatTestCase:
    def __init__(
        self,
        test_id: str,
        query: RedboxQuery,
        test_data: RedboxTestData,
    ):
        # Use separate file_uuids if specified else match the query
        all_s3_keys = test_data.s3_keys if test_data.s3_keys else query.s3_keys

        if (
            test_data.expected_llm_response is not None
            and len(test_data.expected_llm_response) < test_data.number_of_docs
        ):
            log.warning(
                "Number of configured LLM responses might be less than number of docs. For Map-Reduce actions this will give a Generator Error!"
            )

        file_generators = [
            generate_docs(
                s3_key=s3_key,
                total_tokens=int(test_data.tokens_in_all_docs / len(all_s3_keys)),
                number_of_docs=int(test_data.number_of_docs / len(all_s3_keys)),
                chunk_resolution=test_data.chunk_resolution,
            )
            for s3_key in all_s3_keys
        ]
        self.query = query
        self.docs = [doc for generator in file_generators for doc in generator]
        self.test_data = test_data
        self.test_id = test_id

    def get_docs_matching_query(self) -> list[Document]:
        return [
            doc
            for doc in self.docs
            if doc.metadata["file_name"] in set(self.query.s3_keys) & set(self.query.permitted_s3_keys)
        ]

    def get_all_permitted_docs(self) -> list[Document]:
        return [doc for doc in self.docs if doc.metadata["file_name"] in set(self.query.permitted_s3_keys)]


def generate_test_cases(query: RedboxQuery, test_data: list[RedboxTestData], test_id: str) -> list[RedboxChatTestCase]:
    return [
        RedboxChatTestCase(test_id=f"{test_id}-{i}", query=query, test_data=data) for i, data in enumerate(test_data)
    ]


class FakeRetriever(BaseRetriever):
    docs: list[Document]

    def _get_relevant_documents(self, query: str) -> list[Document]:
        return self.docs

    async def _aget_relevant_documents(self, query: str) -> list[Document]:
        return self.docs


def mock_all_chunks_retriever(docs: list[Document]) -> FakeRetriever:
    return FakeRetriever(docs=docs)


def mock_parameterised_retriever(docs: list[Document]) -> FakeRetriever:
    return FakeRetriever(docs=docs)


def mock_metadata_retriever(docs: list[Document]) -> FakeRetriever:
    metadata_only_docs = [Document(page_content="", metadata={**doc.metadata, "embedding": None}) for doc in docs]
    return FakeRetriever(docs=metadata_only_docs)
