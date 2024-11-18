import copy
import itertools
from datetime import UTC, datetime
from uuid import NAMESPACE_DNS, UUID, uuid5

import pytest
from langchain_core.documents.base import Document
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from redbox.models.chain import DocumentState, LLMCallMetadata, RequestMetadata
from redbox.retriever.retrievers import filter_by_elbow
from redbox.test.data import generate_docs
from redbox.transform import (
    combine_documents,
    merge_documents,
    sort_documents,
    structure_documents_by_file_name,
    structure_documents_by_group_and_indices,
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
    ("scores", "target_len"),
    [
        ([2.2, 2, 1.8, 0.2, 0.2, 0.2], 3),
        # ([2.2, 2.1, 2.1, 2, 2, 1.5, 1.3, 0.9, 0.5], 5), # This test case shows our knee detection doesn't work properly?
        ([1, 1, 1, 1, 1, 1], 6),
        ([], 0),
    ],
)
def test_elbow_filter(scores: list[float], target_len: int):
    """Test that documents are filtered after an "elbow" of similarity score."""
    elbow_filter = filter_by_elbow(enabled=True, score_scaling_factor=100, sensitivity=1)

    documents = [Document(page_content="foo", metadata={"score": score}) for score in scores]

    documents_filtered = elbow_filter(documents)

    assert (
        len(documents_filtered) == target_len
    ), f"Expected {target_len} documents to pass. Received: {len(documents_filtered)}"


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


@pytest.mark.parametrize(
    ("n_parent_files", "n_groups", "n_per_group"),
    [
        (1, 1, 1),
        (2, 2, 2),
        (3, 3, 3),
    ],
)
def test_structure_documents_by_group_and_indices(n_parent_files: int, n_groups: int, n_per_group: int):
    def generate_test_groups(n_parent_files: int, n_groups: int, n_per_group: int) -> list[Document]:
        """Creates interleaved groups to similate sorted documents.

        For example, two parent files in two groups with two docs per group
        will produce:

        [
            Document(s3_key="1", index=1),
            Document(s3_key="1", index=2),
            Document(s3_key="2", index=1),
            Document(s3_key="2", index=2),
            Document(s3_key="1", index=3),
            Document(s3_key="1", index=4),
            Document(s3_key="2", index=3),
            Document(s3_key="2", index=4)
        ]
        """
        all_docs = []
        index_counters = {f"s3_key_{file_i + 1}": 1 for file_i in range(n_parent_files)}

        for _, file_i in itertools.product(range(n_groups), range(n_parent_files)):
            s3_key = f"s3_key_{file_i + 1}"
            generated_docs = list(
                generate_docs(s3_key=s3_key, total_tokens=1000, number_of_docs=n_per_group, chunk_resolution="normal")
            )

            for doc in generated_docs:
                doc.metadata["index"] = index_counters[s3_key]
                index_counters[s3_key] += 1
                all_docs.append(doc)

        return all_docs

    docs = generate_test_groups(n_parent_files=n_parent_files, n_groups=n_groups, n_per_group=n_per_group)
    structured_docs = structure_documents_by_group_and_indices(docs)

    assert isinstance(structured_docs, DocumentState)
    assert len(structured_docs.groups) == n_parent_files * n_groups

    for group_uuid, group_docs in structured_docs.groups.items():
        assert isinstance(group_uuid, UUID)
        assert isinstance(group_docs, dict)
        assert len(group_docs) == n_per_group

        for doc in group_docs.values():
            assert doc.metadata["uuid"] in group_docs
            assert group_docs[doc.metadata["uuid"]] == doc


def test_merge_documents():
    """Tests that merge documents will merge the two passes of Elastic correctly.

    Asserts:

    * That the initial list's scores are prioritised
    * That higher scores in the adjacent will push out lower scores in the initial
    * The the result truncates to the length of the initial list
    """
    docs_1 = list(
        generate_docs(s3_key="test_key_1", total_tokens=1000, number_of_docs=3, chunk_resolution="normal", score=1)
    )

    docs_2: list[Document] = []
    for doc in copy.deepcopy(docs_1):
        doc.metadata["score"] = 2
        docs_2.append(doc)

    merged_1 = merge_documents(initial=docs_1, adjacent=docs_2)

    # Initial list score prioritised over adjacent
    assert merged_1 == docs_1

    docs_3 = list(
        generate_docs(s3_key="test_key_2", total_tokens=1000, number_of_docs=3, chunk_resolution="normal", score=3)
    ) + [docs_1[0]]

    merged_2 = merge_documents(initial=docs_1, adjacent=docs_3)

    # Higher scores in adjacent prioritised, length is the same as initial
    assert merged_2 == docs_3[: len(docs_1)]


def test_sort_documents():
    original_order = [
        (5, "foo.txt", 3),
        (4.9, "foo.txt", 2),
        (4.8, "bar.txt", 9),
        (4.1, "foo.txt", 1),
        (3.8, "foo.txt", 24),
    ]
    expected_order = [
        (4.1, "foo.txt", 1),
        (4.9, "foo.txt", 2),
        (5, "foo.txt", 3),
        (4.8, "bar.txt", 9),
        (3.8, "foo.txt", 24),
    ]

    docs: list[Document] = []

    for score, s3_key, index in original_order:
        docs.append(
            next(
                generate_docs(
                    s3_key=s3_key,
                    total_tokens=100,
                    number_of_docs=1,
                    chunk_resolution="normal",
                    index_start=index,
                    score=score,
                )
            )
        )

    sorted_docs = sort_documents(docs)

    for doc, (expected_score, expected_file_name, expected_index) in zip(sorted_docs, expected_order):
        assert doc.metadata["score"] == expected_score
        assert doc.metadata["uri"] == expected_file_name
        assert doc.metadata["index"] == expected_index
