from operator import itemgetter
from typing import Any, TypedDict, List, Dict
from uuid import UUID

from elasticsearch import Elasticsearch
from langchain.schema import StrOutputParser
from langchain_community.chat_models import ChatLiteLLM
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableLambda, RunnablePassthrough, chain
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_elasticsearch import ElasticsearchRetriever

from core_api.src.format import format_chunks
from redbox.models import Chunk, ChatMessage, ChatResponse
from redbox.models.chat import SourceDocument
from redbox.llm.prompts.chat import CONDENSE_QUESTION_PROMPT


def make_chat_prompt_from_messages_runnable(system_prompt: str, question_prompt: str):
    system_prompt_message = [("system", system_prompt)]

    @chain
    def chat_prompt_from_messages(input_dict: Dict):
        """
        Create a ChatPrompTemplate as part of a chain using 'chat_history'.
        Returns the PromptValue using values in the input_dict
        """
        return ChatPromptTemplate.from_messages(
            system_prompt_message
            + [(msg["role"], msg["text"]) for msg in input_dict["chat_history"]]
            + [("user", question_prompt)]
        ).invoke(input_dict)

    return chat_prompt_from_messages


def make_static_response_chain(prompt_template):
    return RunnablePassthrough.assign(
        response=(ChatPromptTemplate.from_template(prompt_template) | RunnableLambda(lambda p: p.messages[0].content)),
        source_documents=RunnableLambda(lambda x: []),
    )


@chain
def map_to_chat_response(input_dict: Dict):
    """
    Create a ChatResponse at the end of a chain from a dict containing
    'response' a string to use as output_text
    'source_documents' a list of chunks to map to source_documents
    """
    return ChatResponse(
        output_text=input_dict["response"],
        source_documents=[
            SourceDocument(
                page_content=chunk.text,
                file_uuid=chunk.parent_file_uuid,
                page_numbers=chunk.metadata.page_number
                if isinstance(chunk.metadata.page_number, list)
                else [chunk.metadata.page_number],
            )
            for chunk in input_dict.get("source_documents", [])
        ],
    )


def make_chat_runnable(
    system_prompt: str,
    llm: ChatLiteLLM,
) -> Runnable:
    """Takes a system prompt and LLM returns a chat runnable.

    Runnable takes input of a dict keyed to question and messages.

    Runnable returns a string.
    """
    chat_history = [
        ("system", system_prompt),
        ("placeholder", "{messages}"),
        ("user", "{question}"),
    ]

    return (
        {
            "question": itemgetter("question"),
            "messages": itemgetter("messages"),
        }
        | ChatPromptTemplate.from_messages(chat_history)
        | llm
        | StrOutputParser()
    )


def make_stuff_document_runnable(
    system_prompt: str,
    llm: ChatLiteLLM,
) -> Runnable:
    """Takes a system prompt and LLM returns a stuff document runnable.

    Runnable takes input of a dict keyed to question, messages and documents.

    Runnable returns a string.
    """
    chat_history = [
        ("system", system_prompt),
        ("placeholder", "{messages}"),
        ("user", "Question: {question}. \n\n Documents: \n\n {documents} \n\n Answer: "),
    ]

    return (
        {"chat_history": itemgetter("chat_history"), "question": itemgetter("question")}
        | CONDENSE_QUESTION_PROMPT
        | llm
        | {
            "question": itemgetter("question"),
            "messages": itemgetter("messages"),
            "documents": itemgetter("documents") | RunnableLambda(format_chunks),
        }
        | ChatPromptTemplate.from_messages(chat_history)
        | llm
        | StrOutputParser()
    )


def make_condense_question_runnable(llm: ChatLiteLLM) -> Runnable:
    """Takes a system prompt and LLM returns a condense question runnable.

    Runnable takes input of a dict keyed to question and messages.

    Runnable returns a string.
    """
    condense_prompt = (
        "Given the following conversation and a follow up question, "
        "rephrase the follow up question to be a standalone question. \n"
        "Chat history:"
    )

    chat_history = [
        ("system", condense_prompt),
        ("placeholder", "{messages}"),
        ("user", "Follow up question: {question}. \nStandalone question: "),
    ]

    return (
        {
            "question": itemgetter("question"),
            "messages": itemgetter("messages"),
        }
        | ChatPromptTemplate.from_messages(chat_history)
        | llm
        | StrOutputParser()
    )


def make_condense_rag_runnable(
    system_prompt: str,
    llm: ChatLiteLLM,
    retriever: VectorStoreRetriever,
) -> Runnable:
    """Takes a system prompt, LLM and retriever and returns a condense RAG runnable.

    This attempts to condense the chat history into a more salient question for the
    LLM to answer, and doesn't pass the entire history on to RAG -- just the condensed
    question.

    Runnable takes input of a dict keyed to question, messages and file_uuids and user_uuid.

    Runnable returns a dict keyed to response and sources.
    """
    chat_history = [
        ("system", system_prompt),
        ("user", "Question: {question}. \n\n Documents: \n\n {documents} \n\n Answer: "),
    ]

    prompt = ChatPromptTemplate.from_messages(chat_history)

    condense_question_runnable = make_condense_question_runnable(llm=llm)

    condense_question_chain = {
        "question": itemgetter("question"),
        "messages": itemgetter("messages"),
    } | condense_question_runnable

    return (
        RunnablePassthrough()
        | {
            "question": condense_question_chain,
            "documents": retriever | format_chunks,
            "sources": retriever,
        }
        | {
            "response": prompt | llm | StrOutputParser(),
            "sources": itemgetter("sources"),
        }
    )
