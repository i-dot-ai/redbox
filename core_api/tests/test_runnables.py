import re

import pytest

from core_api.src.format import format_chunks, get_file_chunked_to_tokens
from core_api.src.routes.chat import build_retrieval_chain
from core_api.src.runnables import make_stuff_document_runnable
from redbox.models.chat import ChatRequest


def test_format_chunks(stored_file_chunks):
    formatted_documents = format_chunks(chunks=stored_file_chunks)

    assert isinstance(formatted_documents, str)
    assert len(list(re.finditer("hello", formatted_documents))) == len(stored_file_chunks)


def test_get_file_chunked_to_tokens(chunked_file, elasticsearch_storage_handler):
    one_document = get_file_chunked_to_tokens(
        file_uuid=chunked_file.uuid,
        user_uuid=chunked_file.creator_user_uuid,
        storage_handler=elasticsearch_storage_handler,
    )

    assert len(one_document) == 1

    many_documents = get_file_chunked_to_tokens(
        file_uuid=chunked_file.uuid,
        user_uuid=chunked_file.creator_user_uuid,
        storage_handler=elasticsearch_storage_handler,
        max_tokens=2,
    )

    assert len(many_documents) > 1


def test_make_stuff_document_runnable(mock_llm, stored_file_chunks):
    chain = make_stuff_document_runnable(
        system_prompt="Your job is summarisation.",
        llm=mock_llm,
    )

    previous_history = [
        {"text": "Lorem ipsum dolor sit amet.", "role": "user"},
        {"text": "Consectetur adipiscing elit.", "role": "ai"},
        {"text": "Donec cursus nunc tortor.", "role": "user"},
    ]

    response = chain.invoke(
        input={
            "question": "Who are all these people?",
            "documents": stored_file_chunks,
            "messages": [(msg["role"], msg["text"]) for msg in previous_history],
        }
    )

    assert response == "<<TESTING>>"


@pytest.mark.asyncio()
async def test_build_retrieval_chain(mock_llm, chunked_file, other_stored_file_chunks, vector_store):  # noqa: ARG001
    request = {
        "message_history": [
            {"text": "hello", "role": "user"},
        ],
        "selected_files": [{"uuid": chunked_file.uuid}],
    }

    docs_with_sources_chain, params = await build_retrieval_chain(
        chat_request=ChatRequest(**request),
        user_uuid=chunked_file.creator_user_uuid,
        llm=mock_llm,
        vector_store=vector_store,
    )

    assert all(doc.metadata["parent_doc_uuid"] == str(chunked_file.uuid) for doc in params["input_documents"])
