from dataclasses import dataclass, field
import datetime
import logging
from uuid import UUID
from typing import Generator

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from redbox.models.chain import RedboxQuery
from redbox.models.chat import ChatRoute
from redbox.models.file import ChunkMetadata, ChunkResolution

log = logging.getLogger()


def generate_docs(
    creator_user_uuid: UUID,
    s3_key: str = "test_data.pdf",
    page_numbers: list[int] = [1, 2, 3, 4],
    total_tokens=6000,
    number_of_docs: int = 10,
    chunk_resolution=ChunkResolution.normal,
) -> Generator[Document, None, None]:
    for i in range(number_of_docs):
        yield Document(
            page_content=f"Document {i} text",
            metadata=ChunkMetadata(
                creator_user_uuid=creator_user_uuid,
                index=i,
                file_name=s3_key,
                page_number=page_numbers[int(i / number_of_docs) * len(page_numbers)],
                created_datetime=datetime.datetime.now(datetime.UTC),
                token_count=int(total_tokens / number_of_docs),
                chunk_resolution=chunk_resolution,
            ).model_dump(),
        )


@dataclass
class RedboxTestData:
    number_of_docs: int
    tokens_in_all_docs: int
    chunk_resolution: ChunkResolution = ChunkResolution.largest
    expected_llm_response: list[str] = field(default_factory=list)
    expected_route: ChatRoute | None = None


class RedboxChatTestCase:
    def __init__(
        self,
        test_id: str,
        query: RedboxQuery,
        test_data: RedboxTestData,
        docs_user_uuid_override: UUID | None = None,
        s3_keys_override: list[str] | None = None,
    ):
        # Use separate file_uuids if specified else match the query
        all_s3_keys = s3_keys_override if s3_keys_override else query.s3_keys
        # Use separate user uuid if specific else match the query
        docs_user_uuid = docs_user_uuid_override if docs_user_uuid_override else query.user_uuid

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
                creator_user_uuid=docs_user_uuid,
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

    def get_docs_matching_query(self):
        return [
            doc
            for doc in self.docs
            if doc.metadata["file_name"] in set(self.query.s3_keys)
            and doc.metadata["creator_user_uuid"] == self.query.user_uuid
        ]


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
