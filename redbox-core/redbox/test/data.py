import datetime
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any, Generator, Sequence
from uuid import uuid4

from langchain_core.documents import Document
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from langchain_core.retrievers import BaseRetriever
from langchain_core.tools import BaseTool
from pydantic.v1 import BaseModel, Field, validator

from redbox.models.chain import RedboxQuery
from redbox.models.chat import ChatRoute, ErrorRoute
from redbox.models.file import ChunkResolution, UploadedFileMetadata
from redbox.models.graph import RedboxActivityEvent

log = logging.getLogger()


def generate_docs(
    s3_key: str = "test_data.pdf",
    page_numbers: list[int] = [1, 2, 3, 4],
    total_tokens: int = 6000,
    number_of_docs: int = 10,
    chunk_resolution: ChunkResolution = ChunkResolution.normal,
    score: int = 1,
    index_start: int = 0,
) -> Generator[Document, None, None]:
    """Generates a list of documents as if retrieved from a real retriever.

    For this reason, adds extra data beyond ChunkMetadata, mimicing
    redbox.retriever.retrievers.hit_to_doc().
    """
    for i in range(number_of_docs):
        core_metadata = UploadedFileMetadata(
            index=index_start + i,
            uri=s3_key,
            page_number=page_numbers[int(i / number_of_docs) * len(page_numbers)],
            created_datetime=datetime.datetime.now(datetime.UTC),
            token_count=int(total_tokens / number_of_docs),
            chunk_resolution=chunk_resolution,
            name=Path(s3_key).stem,
            description="Lorem ipsum dolor sit amet",
            keywords=["foo", "bar"],
        ).model_dump()

        extra_metadata = {
            "score": score,
            "uuid": uuid4(),
        }

        yield Document(
            page_content=f"Document {i} text",
            metadata=core_metadata | extra_metadata,
        )


class RedboxTestData(BaseModel):
    class Config:
        arbitrary_types_allowed = True

    number_of_docs: int
    tokens_in_all_docs: int
    chunk_resolution: ChunkResolution = ChunkResolution.largest
    llm_responses: list[str | AIMessage] = Field(default_factory=list)
    expected_text: str | None = None
    expected_route: ChatRoute | ErrorRoute | None = None
    expected_activity_events: Callable[[list[RedboxActivityEvent]], bool] = Field(
        default=lambda _: True
    )  # Function to check activity events are as expected
    s3_keys: list[str] | None = None

    @validator("llm_responses", pre=True)
    @classmethod
    def coerce_to_aimessage(cls, value: str | AIMessage):
        coerced: list[AIMessage] = []
        for i in value:
            if isinstance(i, str):
                coerced.append(AIMessage(content=i))
            else:
                coerced.append(i)
        return coerced


class RedboxChatTestCase:
    def __init__(
        self,
        test_id: str,
        query: RedboxQuery,
        test_data: RedboxTestData,
    ):
        # Use separate file_uuids if specified else match the query
        all_s3_keys = test_data.s3_keys if test_data.s3_keys else query.s3_keys

        if test_data.llm_responses is not None and len(test_data.llm_responses) < test_data.number_of_docs:
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
            if doc.metadata["uri"] in set(self.query.s3_keys) & set(self.query.permitted_s3_keys)
        ]

    def get_all_permitted_docs(self) -> list[Document]:
        return [doc for doc in self.docs if doc.metadata["uri"] in set(self.query.permitted_s3_keys)]


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


class GenericFakeChatModelWithTools(GenericFakeChatModel):
    """A thin wrapper to GenericFakeChatModel that allows tool binding."""

    tools: Sequence[dict[str, Any] | type | Callable | BaseTool] | None = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def bind_tools(
        self,
        tools: Sequence[dict[str, Any] | type | Callable | BaseTool],
        *args: Any,
        **kwargs: Any,
    ) -> "GenericFakeChatModelWithTools":
        """Bind tool-like objects to this chat model."""
        self.tools = tools
        return self
