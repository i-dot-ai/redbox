import re

from core_api.src.format import format_chunks, get_file_chunked_to_tokens
from core_api.src.runnables import (
    make_chat_runnable,
    make_es_retriever,
    make_rag_runnable,
    make_stuff_document_runnable,
)


def test_make_chat_runnable(mock_llm):
    chain = make_chat_runnable(
        system_prompt="Your job is chat.",
        llm=mock_llm,
    )

    previous_history = [
        {"text": "Lorem ipsum dolor sit amet.", "role": "user"},
        {"text": "Consectetur adipiscing elit.", "role": "ai"},
        {"text": "Donec cursus nunc tortor.", "role": "user"},
    ]

    response = chain.invoke(
        input={
            "question": "How are you today?",
            "messages": [(msg["role"], msg["text"]) for msg in previous_history],
        }
    )

    assert response == "<<TESTING>>"


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


def test_make_es_retriever(es_client, embedding_model, chunked_file, chunk_index_name):
    retriever = make_es_retriever(es=es_client, embedding_model=embedding_model, chunk_index_name=chunk_index_name)

    one_doc_chunks = retriever.invoke(
        input={
            "question": "hello",
            "file_uuids": [chunked_file.uuid],
            "user_uuid": chunked_file.creator_user_uuid,
        }
    )

    assert {chunked_file.uuid} == {chunk.parent_file_uuid for chunk in one_doc_chunks}

    no_doc_chunks = retriever.invoke(
        input={
            "question": "tell me about energy",
            "file_uuids": [],
            "user_uuid": chunked_file.creator_user_uuid,
        }
    )

    assert len(no_doc_chunks) >= 1


def test_make_rag_runnable(es_client, embedding_model, chunk_index_name, mock_llm, chunked_file):
    retriever = make_es_retriever(es=es_client, embedding_model=embedding_model, chunk_index_name=chunk_index_name)

    chain = make_rag_runnable(system_prompt="Your job is Q&A.", llm=mock_llm, retriever=retriever)

    previous_history = [
        {"text": "Lorem ipsum dolor sit amet.", "role": "user"},
        {"text": "Consectetur adipiscing elit.", "role": "ai"},
        {"text": "Donec cursus nunc tortor.", "role": "user"},
    ]

    response = chain.invoke(
        input={
            "question": "Who are all these people?",
            "messages": [(msg["role"], msg["text"]) for msg in previous_history],
            "file_uuids": [chunked_file.uuid],
            "user_uuid": chunked_file.creator_user_uuid,
        }
    )

    assert response["response"] == "<<TESTING>>"
    assert {chunked_file.uuid} == {chunk.parent_file_uuid for chunk in response["sources"]}
