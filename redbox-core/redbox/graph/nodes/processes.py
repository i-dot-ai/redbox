import logging
from operator import attrgetter
import re
from typing import Any, Callable
from uuid import uuid4
from functools import reduce

from langchain.schema import StrOutputParser
from langchain_core.runnables import RunnableParallel, RunnablePassthrough, RunnableLambda
from langchain_core.vectorstores import VectorStoreRetriever

from redbox.chains.components import get_tokeniser, get_chat_llm
from redbox.chains.runnables import build_chat_prompt_from_messages_runnable, CannedChatLLM
from redbox.models import ChatRoute, Settings
from redbox.models.chain import RedboxState
from redbox.transform import combine_documents, structure_documents, to_request_metadata
from redbox.models.chain import PromptSet
from redbox.transform import flatten_document_state


log = logging.getLogger()
re_keyword_pattern = re.compile(r"@(\w+)")


# Patterns: functions that build processes

## Core patterns


def build_retrieve_pattern(
    retriever: VectorStoreRetriever, final_source_chain: bool = False
) -> Callable[[RedboxState], dict[str, Any]]:
    """Returns a function that uses state["request"] and state["text"] to set state["documents"]."""
    retriever = RunnableParallel({"documents": retriever | structure_documents})

    if final_source_chain:
        _retriever = retriever.with_config(tags=["source_documents_flag"])
    else:
        _retriever = retriever

    def _retrieve(state: RedboxState) -> dict[str, Any]:
        return _retriever.invoke(state)

    return _retrieve


def build_chat_pattern(
    prompt_set: PromptSet,
    final_response_chain: bool = False,
) -> Callable[[RedboxState], dict[str, Any]]:
    """Returns a function that uses state["request"] to set state["text"]."""

    def _chat(state: RedboxState) -> dict[str, Any]:
        llm = get_chat_llm(Settings(), state["request"].ai_settings)
        _llm = llm.with_config(tags=["response_flag"]) if final_response_chain else llm
        chat_chain = (
            build_chat_prompt_from_messages_runnable(prompt_set)
            | _llm
            | {
                "text": StrOutputParser(),
                "metadata": RunnableLambda(attrgetter("response_metadata")) | to_request_metadata,
            }
        )

        return chat_chain.invoke(state)

    return _chat


def build_merge_pattern(
    prompt_set: PromptSet,
    final_response_chain: bool = False,
) -> Callable[[RedboxState], dict[str, Any]]:
    """Returns a function that uses state["request"] and state["documents"] to return one item in state["documents"].

    When combined with chunk send, will replace each Document with what's returned from the LLM.

    When combined with group send, with combine all Documents and use the metadata of the first.

    When used without a send, the first Document receieved defines the metadata.
    """
    tokeniser = get_tokeniser()

    def _merge(state: RedboxState) -> dict[str, Any]:
        llm = get_chat_llm(Settings(), state["request"].ai_settings)
        _llm = llm.with_config(tags=["response_flag"]) if final_response_chain else llm

        flattened_documents = flatten_document_state(state["documents"])

        merged_document = reduce(lambda left, right: combine_documents(left, right), flattened_documents)

        merge_chain = (
            build_chat_prompt_from_messages_runnable(prompt_set)
            | _llm
            | {
                "text": StrOutputParser(),
                "metadata": RunnableLambda(attrgetter("response_metadata")) | to_request_metadata,
            }
        )

        merge_state = RedboxState(
            request=state["request"],
            documents={merged_document.metadata["file_name"]: {merged_document.metadata["file_name"]: merged_document}},
        )

        merge_response = merge_chain.invoke(merge_state)
        merged_document.page_content = merge_response["text"]
        request_metadata = merge_response["metadata"]
        merged_document.metadata["token_count"] = len(tokeniser.encode(merged_document.page_content))

        group_uuid = merged_document.metadata.get("file_name", str(uuid4()))
        document_uuid = merged_document.metadata.get("uuid", uuid4())

        # Clear old documents, add new one
        document_state = state["documents"].copy()

        for group in document_state:
            for document in document_state[group]:
                document_state[group][document] = None

        document_state[group_uuid][document_uuid] = merged_document

        return {"documents": document_state, "metadata": request_metadata}

    return _merge


def build_stuff_pattern(
    prompt_set: PromptSet,
    final_response_chain: bool = False,
) -> Callable[[RedboxState], dict[str, Any]]:
    """Returns a function that uses state["request"] and state["documents"] to set state["text"]."""

    def _stuff(state: RedboxState) -> dict[str, Any]:
        llm = get_chat_llm(Settings(), state["request"].ai_settings)
        _llm = llm.with_config(tags=["response_flag"]) if final_response_chain else llm
        return (
            build_chat_prompt_from_messages_runnable(prompt_set)
            | _llm
            | {
                "text": StrOutputParser(),
                "metadata": RunnableLambda(attrgetter("response_metadata")) | to_request_metadata,
            }
        ).invoke(state)

    return _stuff


## Utility patterns


def build_set_route_pattern(route: ChatRoute) -> Callable[[RedboxState], dict[str, Any]]:
    """Returns a function that sets state["route_name"]."""

    def _set_route(state: RedboxState) -> dict[str, Any]:
        set_route_chain = (RunnablePassthrough() | StrOutputParser()).with_config(tags=["route_flag"])

        return {"route_name": set_route_chain.invoke(route.value)}

    return _set_route


def build_passthrough_pattern() -> Callable[[RedboxState], dict[str, Any]]:
    """Returns a function that uses state["request"] to set state["text"]."""

    def _passthrough(state: RedboxState) -> dict[str, Any]:
        return {
            "text": state["request"].question,
        }

    return _passthrough


def build_set_text_pattern(text: str, final_response_chain: bool = False):
    """Returns a function that can arbitrarily set state["text"] to a value."""
    llm = CannedChatLLM(text=text)
    _llm = llm.with_config(tags=["response_flag"]) if final_response_chain else llm

    def _set_text(state: RedboxState) -> dict[str, Any]:
        set_text_chain = _llm | StrOutputParser()

        return {"text": set_text_chain.invoke(text)}

    return _set_text


# Raw processes


def clear_documents_process(state: RedboxState) -> dict[str, Any]:
    return {"documents": {group_id: None for group_id in state["documents"].keys()}}


def empty_process(state: RedboxState) -> None:
    return None
