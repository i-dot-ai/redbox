import logging
import re
from typing import Any

from langchain.schema import StrOutputParser
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import Runnable, RunnableLambda, RunnableParallel
from langchain_core.tools import StructuredTool
from langchain_core.vectorstores import VectorStoreRetriever

from redbox.chains.components import get_chat_llm
from redbox.chains.runnables import CannedChatLLM, build_llm_chain
from redbox.models import ChatRoute
from redbox.models.chain import PromptSet, RedboxState, RequestMetadata
from redbox.models.graph import ROUTE_NAME_TAG, SOURCE_DOCUMENTS_TAG

log = logging.getLogger(__name__)
re_keyword_pattern = re.compile(r"@(\w+)")


# Patterns: functions that build processes

## Core patterns


def build_retrieve_pattern(
    retriever: VectorStoreRetriever,
    final_source_chain: bool = False,
) -> Runnable[RedboxState, dict[str, Any]]:
    """Returns a function that uses state["request"] and state["text"] to set state["documents"].

    Uses structure_func to order the retriever documents for the state.
    """
    retriever_chain = RunnableParallel({"documents": retriever})

    if final_source_chain:
        _retriever = retriever_chain.with_config(tags=[SOURCE_DOCUMENTS_TAG])
    else:
        _retriever = retriever_chain

    return _retriever


def build_chat_pattern(
    prompt_set: PromptSet,
    tools: list[StructuredTool] | None = None,
    final_response_chain: bool = False,
) -> Runnable[RedboxState, dict[str, Any]]:
    """Returns a Runnable that uses the state to set state["text"].

    If tools are supplied, can also set state["tool_calls"].
    """

    def _chat(state: RedboxState) -> dict[str, Any]:
        llm = get_chat_llm(state.request.ai_settings.chat_backend, tools=tools)
        return build_llm_chain(
            prompt_set=prompt_set,
            llm=llm,
            final_response_chain=final_response_chain,
        ).invoke(state)

    return _chat


def build_stuff_pattern(
    prompt_set: PromptSet,
    output_parser: Runnable = None,
    format_instructions: str | None = None,
    tools: list[StructuredTool] | None = None,
    final_response_chain: bool = False,
) -> Runnable[RedboxState, dict[str, Any]]:
    """Returns a Runnable that uses state.request and state.documents to set state.messages.

    If tools are supplied, can also set state.tool_calls.
    """

    @RunnableLambda
    def _stuff(state: RedboxState) -> dict[str, Any]:
        llm = get_chat_llm(state.request.ai_settings.chat_backend, tools=tools)

        events = [
            event
            for event in build_llm_chain(
                prompt_set=prompt_set,
                llm=llm,
                output_parser=output_parser,
                format_instructions=format_instructions,
                final_response_chain=final_response_chain,
            ).stream(state)
        ]
        return sum(events, {})

    return _stuff


## Utility patterns


def build_set_route_pattern(route: ChatRoute) -> Runnable[RedboxState, dict[str, Any]]:
    """Returns a Runnable that sets state["route_name"]."""

    def _set_route(state: RedboxState) -> dict[str, Any]:
        return {"route_name": route}

    return RunnableLambda(_set_route).with_config(tags=[ROUTE_NAME_TAG])


def build_passthrough_pattern() -> Runnable[RedboxState, dict[str, Any]]:
    """Returns a Runnable that uses state["request"] to set state["text"]."""

    @RunnableLambda
    def _passthrough(state: RedboxState) -> dict[str, Any]:
        return {
            "messages": [HumanMessage(content=state.request.question)],
        }

    return _passthrough


def build_set_text_pattern(text: str, final_response_chain: bool = False) -> Runnable[RedboxState, dict[str, Any]]:
    """Returns a Runnable that can arbitrarily set state["messages"] to a value."""
    llm = CannedChatLLM(messages=[AIMessage(content=text)])
    _llm = llm.with_config(tags=["response_flag"]) if final_response_chain else llm

    @RunnableLambda
    def _set_text(state: RedboxState) -> dict[str, Any]:
        set_text_chain = _llm | StrOutputParser()

        return {"messages": state.messages + [HumanMessage(content=set_text_chain.invoke(text))]}

    return _set_text


def build_set_metadata_pattern() -> Runnable[RedboxState, dict[str, Any]]:
    """A Runnable which calculates the static request metadata from the state"""

    @RunnableLambda
    def _set_metadata_pattern(state: RedboxState):
        return {
            "metadata": RequestMetadata(
                selected_files_total_tokens=sum(map(lambda d: d.metadata.get("token_count", 0), state.documents)),
                number_of_selected_files=len(state.request.s3_keys),
            )
        }

    return _set_metadata_pattern


def build_error_pattern(text: str, route_name: str | None) -> Runnable[RedboxState, dict[str, Any]]:
    """A Runnable which sets text and route to record an error"""

    @RunnableLambda
    def _error_pattern(state: RedboxState):
        return build_set_text_pattern(text, final_response_chain=True).invoke(state) | build_set_route_pattern(
            route_name
        ).invoke(state)

    return _error_pattern


# Raw processes: functions that need no building


def clear_documents_process(state: RedboxState) -> dict[str, Any]:
    return {"documents": []}


def empty_process(state: RedboxState) -> None:
    return None
