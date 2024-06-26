import re

import pytest

from core_api.src.app import env
from core_api.src.build_chains import build_retrieval_chain, build_summary_chain
from core_api.src.dependencies import get_es_retriever, get_tokeniser
from core_api.src.format import format_chunks, get_file_chunked_to_tokens
from core_api.src.runnables import (
    make_chat_prompt_from_messages_runnable,
    make_chat_runnable,
    make_condense_question_runnable,
    make_condense_rag_runnable,
)
from redbox.models.chain import ChainInput
from redbox.models.errors import AIError


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


def test_make_chat_prompt_from_messages_runnable(mock_llm):
    chain = (
        make_chat_prompt_from_messages_runnable(
            system_prompt="Your job is chat.",
            question_prompt="{question}\n=========\n Response: ",
            context_window_size=100,
            tokeniser=get_tokeniser(),
        )
        | mock_llm
    )

    # Handles a normal call
    response = chain.invoke(
        input={
            "question": "Lorem ipsum dolor sit amet.",
            "chat_history": [],
        }
    )

    assert response == "<<TESTING>>"

    # Handles a long question
    with pytest.raises(AIError):
        response = chain.invoke(
            input={
                "question": "".join(["Lorem ipsum dolor sit amet. "] * 200),
                "chat_history": [],
            }
        )

    # Handles a long history
    response = chain.invoke(
        input={
            "question": "Lorem ipsum dolor sit amet.",
            "chat_history": [
                {"text": str(i), "role": "user"} if i % 2 == 0 else {"text": str(i), "role": "ai"} for i in range(100)
            ],
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


def test_make_es_retriever(es_client, chunked_file):
    retriever = get_es_retriever(es=es_client, env=env)

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


def test_make_condense_question_runnable(mock_llm):
    chain = make_condense_question_runnable(llm=mock_llm)

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


def test_make_condense_rag_runnable(es_client, mock_llm, chunked_file):
    retriever = get_es_retriever(es=es_client, env=env)

    chain = make_condense_rag_runnable(system_prompt="Your job is Q&A.", llm=mock_llm, retriever=retriever)

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


def test_rag_runnable(es_client, mock_llm, chunked_file, env):
    retriever = get_es_retriever(es=es_client, env=env)
    tokeniser = get_tokeniser()

    chain = build_retrieval_chain(llm=mock_llm, retriever=retriever, tokeniser=tokeniser, env=env)

    previous_history = [
        {"text": "Lorem ipsum dolor sit amet.", "role": "user"},
        {"text": "Consectetur adipiscing elit.", "role": "ai"},
        {"text": "Donec cursus nunc tortor.", "role": "user"},
    ]

    response = chain.invoke(
        input=ChainInput(
            question="Who are all these people?",
            chat_history=previous_history,
            file_uuids=[chunked_file.uuid],
            user_uuid=chunked_file.creator_user_uuid,
        ).model_dump()
    )

    assert response["response"] == "<<TESTING>>"
    assert {chunked_file.uuid} == {chunk.parent_file_uuid for chunk in response["source_documents"]}


def test_summary_runnable(elasticsearch_storage_handler, mock_llm, chunked_file, env):
    tokeniser = get_tokeniser()

    chain = build_summary_chain(
        llm=mock_llm, storage_handler=elasticsearch_storage_handler, tokeniser=tokeniser, env=env
    )

    previous_history = [
        {"text": "Lorem ipsum dolor sit amet.", "role": "user"},
        {"text": "Consectetur adipiscing elit.", "role": "ai"},
        {"text": "Donec cursus nunc tortor.", "role": "user"},
    ]

    response = chain.invoke(
        input=ChainInput(
            question="Who are all these people?",
            chat_history=previous_history,
            file_uuids=[chunked_file.uuid],
            user_uuid=chunked_file.creator_user_uuid,
        ).model_dump()
    )

    assert response["response"] == "<<TESTING>>"
