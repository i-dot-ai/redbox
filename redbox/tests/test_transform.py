from datetime import UTC, datetime
from uuid import uuid4

import pytest
from langchain_core.documents.base import Document

from redbox.transform import combine_documents, map_document_to_source_document

document_created = datetime.now(UTC)


@pytest.mark.parametrize(
    ("document"),
    [
        (
            Document(
                page_content="some random text",
                metadata={"_source": {"metadata": {"parent_file_uuid": uuid4(), "page_number": 1}}},
            )
        ),
        (
            Document(
                page_content="some random text2",
                metadata={"_source": {"metadata": {"parent_file_uuid": uuid4(), "page_number": [1, 2]}}},
            )
        ),
        (
            Document(
                page_content="some random text3",
                metadata={
                    "_source": {
                        "metadata": {
                            "parent_file_uuid": uuid4(),
                        }
                    }
                },
            )
        ),
    ],
)
def test_map_document_to_source_document(document: Document):
    """
    Test that documents as pulled by the Elasticsearch retriever get properly mapped to source documents
    """
    source_doc = map_document_to_source_document(document)
    assert source_doc.page_content == document.page_content
    document_page_number = document.metadata["_source"]["metadata"].get("page_number")
    if isinstance(document_page_number, int):
        assert document_page_number in source_doc.page_numbers or {}
        assert len(source_doc.page_numbers or {}) == 1
    elif isinstance(document_page_number, list):
        assert isinstance(source_doc.page_numbers, list)
        assert set(document_page_number) == set(source_doc.page_numbers)
    else:
        assert source_doc.page_numbers == []
    assert source_doc.file_uuid == document.metadata["_source"]["metadata"]["parent_file_uuid"]


@pytest.mark.parametrize(
    ("a", "b", "combined"),
    [
        (
            Document(
                page_content="some random text",
                metadata={
                    "_source": {
                        "metadata": {
                            "parent_file_uuid": "abcd",
                            "creator_user_uuid": "xabcd",
                            "index": 1,
                            "page_number": 1,
                            "languages": ["en"],
                            "link_texts": ["alinktext"],
                            "link_urls": ["alinkurl"],
                            "links": ["alink"],
                            "created_datetime": document_created,
                            "token_count": 27,
                        }
                    }
                },
            ),
            Document(
                page_content="some random text2",
                metadata={
                    "_source": {
                        "metadata": {
                            "parent_file_uuid": "abcd",
                            "creator_user_uuid": "xabcd",
                            "index": 2,
                            "page_number": 2,
                            "languages": ["fr"],
                            "link_texts": ["alinktext2"],
                            "link_urls": ["alinkurl2"],
                            "links": ["alink2"],
                            "created_datetime": datetime.now(UTC),
                            "token_count": 33,
                        }
                    }
                },
            ),
            Document(
                page_content="some random textsome random text2",
                metadata={
                    "_source": {
                        "metadata": {
                            "parent_file_uuid": "abcd",
                            "creator_user_uuid": "xabcd",
                            "index": 1,
                            "page_number": [1, 2],
                            "languages": ["en", "fr"],
                            "link_texts": ["alinktext", "alinktext2"],
                            "link_urls": ["alinkurl", "alinkurl2"],
                            "links": ["alink", "alink2"],
                            "created_datetime": document_created,
                            "token_count": 60,
                        }
                    }
                },
            ),
        ),
        (
            Document(
                page_content="some random text",
                metadata={
                    "_source": {
                        "metadata": {
                            "parent_file_uuid": "asdf",
                            "creator_user_uuid": "xabcd",
                            "index": 10,
                            "page_number": [1, 2],
                            "languages": ["en"],
                            "link_texts": ["alinktext"],
                            "link_urls": ["alinkurl"],
                            "links": ["alink"],
                            "created_datetime": document_created,
                            "token_count": 12,
                        }
                    }
                },
            ),
            Document(
                page_content="some random text2",
                metadata={
                    "_source": {
                        "metadata": {
                            "parent_file_uuid": "asdf",
                            "creator_user_uuid": "xabcd",
                            "index": 12,
                            "page_number": 3,
                            "languages": [],
                            # "link_texts": [],
                            "link_urls": [],
                            "links": [],
                            "created_datetime": datetime.now(UTC),
                            "token_count": 10,
                        }
                    }
                },
            ),
            Document(
                page_content="some random textsome random text2",
                metadata={
                    "_source": {
                        "metadata": {
                            "parent_file_uuid": "asdf",
                            "creator_user_uuid": "xabcd",
                            "index": 10,
                            "page_number": [1, 2, 3],
                            "languages": ["en"],
                            "link_texts": ["alinktext"],
                            "link_urls": ["alinkurl"],
                            "links": ["alink"],
                            "created_datetime": document_created,
                            "token_count": 22,
                        }
                    }
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
        return test_combined.metadata["_source"]["metadata"].get(field_name)

    assert combined.page_content == test_combined.page_content
    for field_name in combined.metadata["_source"]["metadata"]:
        assert get_field(combined, field_name) == get_field(test_combined, field_name)
