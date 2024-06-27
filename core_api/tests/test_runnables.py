from core_api.src.app import env
from core_api.src.build_chains import build_retrieval_chain, build_summary_chain
from core_api.src.dependencies import get_parameterised_retriever
from core_api.src.runnables import (
    make_chat_runnable,
    make_condense_question_runnable,
    make_condense_rag_runnable,
)
from redbox.models.chain import ChainInput


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
    retriever = get_parameterised_retriever(es=es_client, env=env)

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
    assert {str(chunked_file.uuid)} == {chunk.metadata["_source"]["parent_file_uuid"] for chunk in response["sources"]}


def test_rag_runnable(es_client, mock_llm, chunked_file, env):
    retriever = get_parameterised_retriever(es=es_client, env=env)

    chain = build_retrieval_chain(llm=mock_llm, retriever=retriever, env=env)

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
    assert {str(chunked_file.uuid)} == {
        chunk.metadata["_source"]["parent_file_uuid"] for chunk in response["source_documents"]
    }


def test_summary_runnable(all_chunks_retriever, mock_llm, chunked_file, env):
    chain = build_summary_chain(llm=mock_llm, all_chunks_retriever=all_chunks_retriever, env=env)

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
