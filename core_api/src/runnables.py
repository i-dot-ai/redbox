from functools import partial, reduce
from operator import itemgetter

from langchain.schema import StrOutputParser
from langchain_community.chat_models import ChatLiteLLM
from langchain_core.documents.base import Document
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.runnables import (
    Runnable,
    RunnableLambda,
    RunnablePassthrough,
    chain,
)
from langchain_core.vectorstores import VectorStoreRetriever
from tiktoken import Encoding

from core_api.src.format import format_documents, reduce_chunks_by_tokens
from redbox.models import ChatResponse
from redbox.models.errors import AIError
from redbox.transform import map_document_to_source_document


def make_chat_prompt_from_messages_runnable(
    system_prompt: str,
    question_prompt: str,
    input_token_budget: int,
    tokeniser: Encoding,
):
    system_prompt_message = [("system", system_prompt)]
    prompts_budget = len(tokeniser.encode(system_prompt)) - len(tokeniser.encode(question_prompt))
    token_budget = input_token_budget - prompts_budget

    @chain
    def chat_prompt_from_messages(input_dict: dict):
        """
        Create a ChatPrompTemplate as part of a chain using 'chat_history'.
        Returns the PromptValue using values in the input_dict
        """
        chat_history_budget = token_budget - len(tokeniser.encode(input_dict["question"]))

        if chat_history_budget <= 0:
            message = "Question length exceeds context window."
            raise AIError(message)

        truncated_history: list[dict[str, str]] = []
        for msg in input_dict["chat_history"][::-1]:
            chat_history_budget -= len(tokeniser.encode(msg["text"]))
            if chat_history_budget <= 0:
                break
            else:
                truncated_history.insert(0, msg)

        return ChatPromptTemplate.from_messages(
            system_prompt_message
            + [(msg["role"], msg["text"]) for msg in truncated_history]
            + [("user", question_prompt)]
        ).invoke(input_dict)

    return chat_prompt_from_messages


@chain
def map_to_chat_response(input_dict: dict):
    """
    Create a ChatResponse at the end of a chain from a dict containing
    'response' a string to use as output_text
    'source_documents' a list of documents to map to source_documents
    """
    return (
        RunnablePassthrough.assign(
            source_documents=(
                RunnableLambda(lambda d: d.get("source_documents", []))
                | RunnableLambda(lambda docs: list(map(map_document_to_source_document, docs)))
            )
        )
        | RunnableLambda(
            lambda d: ChatResponse(
                output_text=d["response"], source_documents=d.get("source_documents", []), route_name=d["route_name"]
            )
        )
    ).invoke(input_dict)


def make_chat_runnable(system_prompt: str, llm: ChatLiteLLM) -> Runnable:
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


def make_stuff_document_runnable(system_prompt: str, question_prompt: str, llm: ChatLiteLLM) -> Runnable:
    """Takes a system prompt and LLM returns a stuff document runnable.

    Runnable takes input of a dict keyed to question, messages and documents.

    Runnable returns a string.
    """
    chat_history = [
        ("system", system_prompt),
        ("placeholder", "{messages}"),
        (
            "user",
            "Question: {question}. \n\n Documents: \n\n {documents} \n\n Answer: ",
        ),
    ]

    return (
        {"chat_history": itemgetter("chat_history"), "question": itemgetter("question")}
        | PromptTemplate.from_template(question_prompt)
        | llm
        | {
            "question": itemgetter("question"),
            "messages": itemgetter("messages"),
            "documents": itemgetter("documents") | RunnableLambda(format_documents),
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
        (
            "user",
            "Question: {question}. \n\n Documents: \n\n {documents} \n\n Answer: ",
        ),
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
            "documents": retriever | format_documents,
            "sources": retriever,
        }
        | {
            "response": prompt | llm | StrOutputParser(),
            "sources": itemgetter("sources"),
        }
    )


def resize_documents(max_tokens: int | None = None) -> list[Document]:
    """Gets a file as larger document-sized Chunks, splitting it by max_tokens."""
    n = max_tokens or float("inf")

    @chain
    def wrapped(chunks_unsorted: list[Document]):
        chunks_sorted = sorted(chunks_unsorted, key=lambda doc: doc.metadata["index"])
        reduce_chunk_n = partial(reduce_chunks_by_tokens, max_tokens=n)
        return reduce(lambda cs, c: reduce_chunk_n(cs, c), chunks_sorted, [])

    return wrapped
