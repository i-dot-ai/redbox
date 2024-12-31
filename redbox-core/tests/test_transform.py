from datetime import UTC, datetime
from uuid import NAMESPACE_DNS, uuid5

import pytest
from langchain_core.documents.base import Document
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from redbox.models.chain import DocumentState, LLMCallMetadata, RequestMetadata
from redbox.test.data import generate_docs
from redbox.transform import (
    combine_documents,
    structure_documents_by_file_name,
    to_request_metadata,
)

document_created = datetime.now(UTC)


@pytest.mark.parametrize(
    ("a", "b", "combined"),
    [
        (
            Document(
                page_content="these are four tokens ",
                metadata={
                    "file_name": "abcd",
                    "creator_user_uuid": "xabcd",
                    "index": 1,
                    "page_number": 1,
                    "languages": ["en"],
                    "link_texts": ["alinktext"],
                    "link_urls": ["alinkurl"],
                    "links": ["alink"],
                    "created_datetime": document_created,
                    "token_count": 4,
                },
            ),
            Document(
                page_content="these are three",
                metadata={
                    "file_name": "abcd",
                    "creator_user_uuid": "xabcd",
                    "index": 2,
                    "page_number": 2,
                    "languages": ["fr"],
                    "link_texts": ["alinktext2"],
                    "link_urls": ["alinkurl2"],
                    "links": ["alink2"],
                    "created_datetime": datetime.now(UTC),
                    "token_count": 3,
                },
            ),
            Document(
                page_content="these are four tokens these are three",
                metadata={
                    "file_name": "abcd",
                    "creator_user_uuid": "xabcd",
                    "index": 1,
                    "page_number": [1, 2],
                    "languages": ["en", "fr"],
                    "link_texts": ["alinktext", "alinktext2"],
                    "link_urls": ["alinkurl", "alinkurl2"],
                    "links": ["alink", "alink2"],
                    "created_datetime": document_created,
                    "token_count": 7,
                },
            ),
        ),
        (
            Document(
                page_content="there are six tokens right here ",
                metadata={
                    "file_name": "asdf",
                    "creator_user_uuid": "xabcd",
                    "index": 10,
                    "page_number": [1, 2],
                    "languages": ["en"],
                    "link_texts": ["alinktext"],
                    "link_urls": ["alinkurl"],
                    "links": ["alink"],
                    "created_datetime": document_created,
                    "token_count": 6,
                },
            ),
            Document(
                page_content="these are three",
                metadata={
                    "file_name": "asdf",
                    "creator_user_uuid": "xabcd",
                    "index": 12,
                    "page_number": 3,
                    "languages": [],
                    # "link_texts": [],
                    "link_urls": [],
                    "links": [],
                    "created_datetime": datetime.now(UTC),
                    "token_count": 3,
                },
            ),
            Document(
                page_content="there are six tokens right here these are three",
                metadata={
                    "file_name": "asdf",
                    "creator_user_uuid": "xabcd",
                    "index": 10,
                    "page_number": [1, 2, 3],
                    "languages": ["en"],
                    "link_texts": ["alinktext"],
                    "link_urls": ["alinkurl"],
                    "links": ["alink"],
                    "created_datetime": document_created,
                    "token_count": 9,
                },
            ),
        ),
    ],
)
def test_combine_documents(a: Document, b: Document, combined: Document):
    """
    Test that documents as pulled by the Elasticsearch retriever get properly mapped to source documents
    """
    test_combined = combine_documents(a, b)

    def get_field(document, field_name):
        return document.metadata.get(field_name)

    assert combined.page_content == test_combined.page_content
    for field_name in combined.metadata:
        assert get_field(combined, field_name) == get_field(test_combined, field_name)


@pytest.mark.parametrize(
    ("output", "expected"),
    [
        (
            {
                "prompt": "Lorem ipsum dolor sit amet.",
                "model": "gpt-4o",
                "text_and_tools": {
                    "raw_response": AIMessage(
                        content=(
                            "Lorem ipsum dolor sit amet, consectetur adipiscing elit, "
                            "sed do eiusmod tempor incididunt ut labore et dolore magna "
                            "aliqua. "
                        )
                    )
                },
            },
            RequestMetadata(llm_calls={LLMCallMetadata(llm_model_name="gpt-4o", input_tokens=6, output_tokens=23)}),
        ),
        (
            {
                "prompt": "Lorem ipsum dolor sit amet.",
                "model": "unknown-model",
                "text_and_tools": {
                    "raw_response": AIMessage(
                        content=(
                            "Lorem ipsum dolor sit amet, consectetur adipiscing elit, "
                            "sed do eiusmod tempor incididunt ut labore et dolore magna "
                            "aliqua. "
                        )
                    )
                },
            },
            RequestMetadata(
                llm_calls={LLMCallMetadata(llm_model_name="unknown-model", input_tokens=6, output_tokens=23)}
            ),
        ),
    ],
)
def test_to_request_metadata(output: dict, expected: RequestMetadata):
    result = RunnableLambda(to_request_metadata).invoke(output)
    # We assert on token counts here as the id generation causes the LLMCallMetadata objects not to match
    assert (
        result.input_tokens == expected.input_tokens
    ), f"Expected: {expected.input_tokens} Result: {result.input_tokens}"
    assert (
        result.output_tokens == expected.output_tokens
    ), f"Expected: {expected.output_tokens} Result: {result.output_tokens}"


def test_structure_documents_by_file_name():
    docs = list(generate_docs(s3_key="s3_key", total_tokens=1000, number_of_docs=3, chunk_resolution="normal"))
    expected = DocumentState(groups={uuid5(NAMESPACE_DNS, "s3_key"): {doc.metadata["uuid"]: doc for doc in docs}})
    result = structure_documents_by_file_name(docs=docs)

    assert result == expected
