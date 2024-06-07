import re

from langchain.schema import Document

from core_api.src.format import format_docs, get_file_as_documents
from core_api.src.runnables import make_stuff_document_runnable


def test_format_docs():
    documents = [Document(page_content="Test")] * 3
    formatted_documents = format_docs(docs=documents)

    assert isinstance(formatted_documents, str)
    assert len(list(re.finditer("Test", formatted_documents))) == 3


def test_get_file_as_documents(chunked_file, elasticsearch_storage_handler):
    one_document = get_file_as_documents(
        file_uuid=chunked_file.uuid,
        user_uuid=chunked_file.creator_user_uuid,
        storage_handler=elasticsearch_storage_handler,
    )

    assert len(one_document) == 1

    many_documents = get_file_as_documents(
        file_uuid=chunked_file.uuid,
        user_uuid=chunked_file.creator_user_uuid,
        storage_handler=elasticsearch_storage_handler,
        max_tokens=2,
    )

    assert len(many_documents) > 1


def test_make_stuff_document_runnable(mock_llm):
    chain = make_stuff_document_runnable(
        system_prompt="Your job is summarisation.",
        llm=mock_llm,
    )

    previous_history = [
        {"text": "Lorem ipsum dolor sit amet.", "role": "user"},
        {"text": "Consectetur adipiscing elit.", "role": "ai"},
        {"text": "Donec cursus nunc tortor.", "role": "user"},
    ]
    documents = [Document(page_content="Test")] * 3

    response = chain.invoke(
        input={
            "question": "Who are all these people?",
            "documents": documents,
            "messages": [(msg["role"], msg["text"]) for msg in previous_history],
        }
    )

    assert response == "<<TESTING>>"
