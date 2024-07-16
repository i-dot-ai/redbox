from functools import partial, reduce
from typing import Any

from langchain_core.documents.base import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough, chain, Runnable
from tiktoken import Encoding
from kneed import KneeLocator

from redbox.api.format import reduce_chunks_by_tokens
from redbox.models import ChatResponse
from redbox.models.errors import QuestionLengthError
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
            raise QuestionLengthError

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


def resize_documents(max_tokens: int | None = None) -> Runnable[list[Document], Any]:
    """Gets a file as larger document-sized Chunks, splitting it by max_tokens."""
    n = max_tokens or float("inf")

    @chain
    def wrapped(chunks_unsorted: list[Document]):
        chunks_sorted = sorted(chunks_unsorted, key=lambda doc: doc.metadata["index"])
        reduce_chunk_n = partial(reduce_chunks_by_tokens, max_tokens=n)
        return reduce(lambda cs, c: reduce_chunk_n(cs, c), chunks_sorted, [])  # type: ignore

    return wrapped


# TODO: allow for nothing coming back/empty list -- don't error
# https://github.com/i-dot-ai/redbox/actions/runs/9944427706/job/27470465428#step:10:7160


def filter_by_elbow(enabled: bool = True) -> Runnable[list[Document], list[Document]]:
    """Filters a list of documents by the elbow point on the curve of their scores.

    Args:
        enabled (bool, optional): Whether to enable the filter. Defaults to True.
    Returns:
        callable: A function that takes a list of documents and returns a list of documents.
    """

    @chain
    def _filter_by_elbow(docs: list[Document]):
        # If enabled, return only the documents up to the elbow point
        if enabled:
            if len(docs) == 0:
                return docs
            
            # *100 because algorithm performs poorly on changes of ~1.0
            try:
                scores = [doc.metadata["score"] * 100 for doc in docs]
            except AttributeError as exc:
                raise exc

            rank = range(len(scores))

            # Convex curve, decreasing direction as scores descend in a pareto-like fashion
            kn = KneeLocator(rank, scores, curve="convex", direction="decreasing")
            return docs[: kn.elbow]
        else:
            return docs

    return _filter_by_elbow
