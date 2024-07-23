from langchain_core.documents.base import Document

ALL_CHUNKS_RETRIEVER_DOCUMENTS = [
    [
        Document(
            page_content="ABC",
            metadata={
                "parent_file_uuid": "abcd",
                "creator_user_uuid": "xabcd",
                "index": 1,
                "page_number": 1,
                "languages": ["en"],
                "link_texts": [],
                "link_urls": [],
                "links": [],
                "created_datetime": "2024-06-01T12:00:00Z",
                "token_count": 12,
                "chunk_resolution": "largest",
            },
        ),
        Document(
            page_content="DEF",
            metadata={
                "parent_file_uuid": "abcd",
                "creator_user_uuid": "xabcd",
                "index": 2,
                "page_number": 1,
                "languages": ["en"],
                "link_texts": [],
                "link_urls": [],
                "links": [],
                "created_datetime": "2024-06-01T12:00:00Z",
                "token_count": 12,
                "chunk_resolution": "largest",
            },
        ),
        Document(
            page_content="GHI",
            metadata={
                "parent_file_uuid": "abcd",
                "creator_user_uuid": "xabcd",
                "index": 3,
                "page_number": 1,
                "languages": ["en"],
                "link_texts": [],
                "link_urls": [],
                "links": [],
                "created_datetime": "2024-06-01T12:00:00Z",
                "token_count": 12,
                "chunk_resolution": "largest",
            },
        ),
        Document(
            page_content="JKL",
            metadata={
                "parent_file_uuid": "abcd",
                "creator_user_uuid": "xabcd",
                "index": 4,
                "page_number": 1,
                "languages": ["en"],
                "link_texts": [],
                "link_urls": [],
                "links": [],
                "created_datetime": "2024-06-01T12:00:00Z",
                "token_count": 12,
                "chunk_resolution": "largest",
            },
        ),
    ]
]

PARAMETERISED_RETRIEVER_DOCUMENTS = [
    [
        Document(
            page_content="ABC",
            metadata={
                "parent_file_uuid": "abcd",
                "creator_user_uuid": "xabcd",
                "index": 1,
                "page_number": 1,
                "languages": ["en"],
                "link_texts": [],
                "link_urls": [],
                "links": [],
                "created_datetime": "2024-06-01T12:00:00Z",
                "token_count": 12,
                "chunk_resolution": "normal",
            },
        ),
        Document(
            page_content="DEF",
            metadata={
                "parent_file_uuid": "abcd",
                "creator_user_uuid": "xabcd",
                "index": 2,
                "page_number": 1,
                "languages": ["en"],
                "link_texts": [],
                "link_urls": [],
                "links": [],
                "created_datetime": "2024-06-01T12:00:00Z",
                "token_count": 12,
                "chunk_resolution": "normal",
            },
        ),
        Document(
            page_content="GHI",
            metadata={
                "parent_file_uuid": "abcd",
                "creator_user_uuid": "xabcd",
                "index": 3,
                "page_number": 1,
                "languages": ["en"],
                "link_texts": [],
                "link_urls": [],
                "links": [],
                "created_datetime": "2024-06-01T12:00:00Z",
                "token_count": 12,
                "chunk_resolution": "normal",
            },
        ),
        Document(
            page_content="JKL",
            metadata={
                "parent_file_uuid": "abcd",
                "creator_user_uuid": "xabcd",
                "index": 4,
                "page_number": 1,
                "languages": ["en"],
                "link_texts": [],
                "link_urls": [],
                "links": [],
                "created_datetime": "2024-06-01T12:00:00Z",
                "token_count": 12,
                "chunk_resolution": "normal",
            },
        ),
    ]
]
