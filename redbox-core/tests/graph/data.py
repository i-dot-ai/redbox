from dataclasses import dataclass
import datetime
from uuid import UUID

from langchain_core.documents import Document

from redbox.models.chain import ChainInput
from redbox.models.chat import ChatRoute
from redbox.models.file import ChunkMetadata, ChunkResolution


def generate_docs(
    parent_file_uuid: UUID,
    creator_user_uuid: UUID,
    file_name: str = "test_data.pdf",
    page_numbers: list[int] = [1, 2, 3, 4],
    total_tokens=6000,
    number_of_docs: int = 10,
    chunk_resolution=ChunkResolution.normal,
):
    for i in range(number_of_docs):
        yield Document(
            page_content=f"Document {i} text",
            metadata=ChunkMetadata(
                parent_file_uuid=parent_file_uuid,
                creator_user_uuid=creator_user_uuid,
                index=i,
                file_name=file_name,
                page_number=page_numbers[int(i / number_of_docs) * len(page_numbers)],
                created_datetime=datetime.datetime.now(datetime.UTC),
                token_count=int(total_tokens / number_of_docs),
                chunk_resolution=chunk_resolution,
            ).model_dump(),
        )


@dataclass
class TestData:
    number_of_docs: int
    tokens_in_all_docs: int
    expected_llm_response: list[str]
    expected_route: ChatRoute


class RedboxChatTestCase:
    def __init__(
        self,
        query: ChainInput,
        test_data: TestData,
        docs_user_uuid_override: UUID = None,
        docs_file_uuids_override: list[UUID] = None,
    ):
        # Use separate file_uuids if specified else match the query
        all_file_uuids = docs_file_uuids_override if docs_file_uuids_override else [id for id in query.file_uuids]
        # Use separate user uuid if specific else match the query
        docs_user_uuid = docs_user_uuid_override if docs_user_uuid_override else query.user_uuid
        file_generators = [
            generate_docs(
                parent_file_uuid=file_uuid,
                creator_user_uuid=docs_user_uuid,
                total_tokens=test_data.tokens_in_all_docs,
                number_of_docs=test_data.number_of_docs,
                chunk_resolution=ChunkResolution.largest,
            )
            for file_uuid in all_file_uuids
        ]
        self.query = query
        self.docs = [doc for generator in file_generators for doc in generator]
        self.llm_response = test_data.expected_llm_response
        self.expected_route = test_data.expected_route


def generate_test_cases(query: ChainInput, test_data: list[TestData]):
    return [RedboxChatTestCase(query=query, test_data=data) for data in test_data]
