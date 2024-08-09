import pytest
from core_api.build_chains import (
    build_chat_chain,
    build_chat_with_docs_chain,
    build_condense_retrieval_chain,
    build_retrieval_chain,
)
from core_api.dependencies import get_parameterised_retriever, get_tokeniser

from redbox.api.runnables import make_chat_prompt_from_messages_runnable
from redbox.models.chain import ChainInput
from redbox.models.chat import ChatRoute
from redbox.models.errors import AIError


@pytest.fixture(scope="module", autouse=True)
def mock_embeddings(session_mocker, embedding_model):
    session_mocker.patch("core_api.dependencies.get_embedding_model", return_value=embedding_model)
    return embedding_model


def test_make_chat_prompt_from_messages_runnable(mock_llm):
    chain = (
        make_chat_prompt_from_messages_runnable(
            system_prompt="Your job is chat.",
            question_prompt="{question}\n=========\n Response: ",
            input_token_budget=100,
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


def test_rag_runnable(mock_llm, chunked_file, env):
    retriever = get_parameterised_retriever(
        env=env,
    )

    chain = build_retrieval_chain(llm=mock_llm, retriever=retriever, tokeniser=get_tokeniser(), env=env)

    previous_history = [
        {"text": "Lorem ipsum dolor sit amet.", "role": "user"},
        {"text": "Consectetur adipiscing elit.", "role": "ai"},
        {"text": "Donec cursus nunc tortor.", "role": "user"},
    ]

    response = chain.invoke(
        input=ChainInput(
            question="Who are all these people?",
            chat_history=previous_history,
            file_uuids=[str(chunked_file.uuid)],
            user_uuid=str(chunked_file.creator_user_uuid),
        ).dict()
    )

    assert response["response"] == "<<TESTING>>"
    assert {str(chunked_file.uuid)} == {chunk.metadata["parent_file_uuid"] for chunk in response["source_documents"]}


def test_condense_runnable(mock_llm, chunked_file, env):
    retriever = get_parameterised_retriever(env=env)

    chain = build_condense_retrieval_chain(llm=mock_llm, retriever=retriever, tokeniser=get_tokeniser(), env=env)

    previous_history = [
        {"text": "Lorem ipsum dolor sit amet.", "role": "user"},
        {"text": "Consectetur adipiscing elit.", "role": "ai"},
        {"text": "Donec cursus nunc tortor.", "role": "user"},
    ]

    response = chain.invoke(
        input=ChainInput(
            question="Who are all these people?",
            chat_history=previous_history,
            file_uuids=[str(chunked_file.uuid)],
            user_uuid=str(chunked_file.creator_user_uuid),
        ).dict()
    )
    assert response["response"] == "<<TESTING>>"
    assert response["route_name"].startswith("search")
    all_results_file_uuids = {chunk.metadata["parent_file_uuid"] for chunk in response["source_documents"]}
    assert {
        str(chunked_file.uuid)
    } == all_results_file_uuids, f"Expected {str(chunked_file.uuid)} in {all_results_file_uuids}"


def test_chat_runnable(mock_llm, chunked_file, env):
    chain = build_chat_chain(llm=mock_llm, tokeniser=get_tokeniser(), env=env)

    previous_history = [
        {"text": "Lorem ipsum dolor sit amet.", "role": "user"},
        {"text": "Consectetur adipiscing elit.", "role": "ai"},
        {"text": "Donec cursus nunc tortor.", "role": "user"},
    ]

    response = chain.invoke(
        input=ChainInput(
            question="Who are all these people?",
            chat_history=previous_history,
            file_uuids=[str(chunked_file.uuid)],
            user_uuid=str(chunked_file.creator_user_uuid),
        ).dict()
    )

    assert response["response"] == "<<TESTING>>"
    assert response["route_name"] == ChatRoute.chat


def test_chat_with_documents_runnable(all_chunks_retriever, mock_llm, chunked_file, env):
    chain = build_chat_with_docs_chain(
        llm=mock_llm, all_chunks_retriever=all_chunks_retriever, tokeniser=get_tokeniser(), env=env
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
            file_uuids=[str(chunked_file.uuid)],
            user_uuid=str(chunked_file.creator_user_uuid),
        ).dict()
    )

    assert response["response"] == "<<TESTING>>"
    assert response["route_name"] == ChatRoute.chat_with_docs
