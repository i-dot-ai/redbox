import json
import logging
import re
import textwrap
from collections.abc import Callable
from functools import reduce
from typing import Any, Iterable
from uuid import uuid4

from langchain.schema import StrOutputParser
from langchain_core.callbacks.manager import dispatch_custom_event
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import Runnable, RunnableLambda, RunnableParallel
from langchain_core.tools import StructuredTool
from langchain_core.vectorstores import VectorStoreRetriever

from redbox.chains.activity import log_activity
from redbox.chains.components import get_chat_llm, get_tokeniser
from redbox.chains.runnables import CannedChatLLM, build_llm_chain
from redbox.graph.nodes.tools import get_log_formatter_for_retrieval_tool, has_injected_state, is_valid_tool
from redbox.models import ChatRoute
from redbox.models.chain import DocumentState, PromptSet, RedboxState, RequestMetadata, merge_redbox_state_updates
from redbox.models.graph import ROUTE_NAME_TAG, SOURCE_DOCUMENTS_TAG, RedboxActivityEvent, RedboxEventType
from redbox.transform import combine_documents, flatten_document_state

log = logging.getLogger(__name__)
re_keyword_pattern = re.compile(r"@(\w+)")


# Patterns: functions that build processes

## Core patterns


def build_retrieve_pattern(
    retriever: VectorStoreRetriever,
    structure_func: Callable[[list[Document]], DocumentState],
    final_source_chain: bool = False,
) -> Runnable[RedboxState, dict[str, Any]]:
    """Returns a function that uses state["request"] and state["text"] to set state["documents"].

    Uses structure_func to order the retriever documents for the state.
    """
    retriever_chain = RunnableParallel({"documents": retriever | structure_func})

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
        llm = get_chat_llm(state["request"].ai_settings.chat_backend, tools=tools)
        return build_llm_chain(
            prompt_set=prompt_set,
            llm=llm,
            final_response_chain=final_response_chain,
        ).invoke(state)

    return _chat


def build_merge_pattern(
    prompt_set: PromptSet,
    tools: list[StructuredTool] | None = None,
    final_response_chain: bool = False,
) -> Runnable[RedboxState, dict[str, Any]]:
    """Returns a Runnable that uses state["request"] and state["documents"] to return one item in state["documents"].

    When combined with chunk send, will replace each Document with what's returned from the LLM.

    When combined with group send, with combine all Documents and use the metadata of the first.

    When used without a send, the first Document receieved defines the metadata.

    If tools are supplied, can also set state["tool_calls"].
    """
    tokeniser = get_tokeniser()

    @RunnableLambda
    def _merge(state: RedboxState) -> dict[str, Any]:
        llm = get_chat_llm(state["request"].ai_settings.chat_backend, tools=tools)

        if not state.get("documents"):
            return {"documents": None}

        flattened_documents = flatten_document_state(state["documents"])

        merged_document = reduce(lambda left, right: combine_documents(left, right), flattened_documents)

        merge_state = RedboxState(
            request=state["request"],
            documents={merged_document.metadata["uri"]: {merged_document.metadata["uuid"]: merged_document}},
        )

        merge_response = build_llm_chain(
            prompt_set=prompt_set, llm=llm, final_response_chain=final_response_chain
        ).invoke(merge_state)

        merged_document.page_content = merge_response["messages"][-1].content
        request_metadata = merge_response["metadata"]
        merged_document.metadata["token_count"] = len(tokeniser.encode(merged_document.page_content))

        group_uuid = next(iter(state["documents"] or {}), uuid4())
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
    output_parser: Runnable = None,
    format_instructions: str | None = None,
    tools: list[StructuredTool] | None = None,
    final_response_chain: bool = False,
) -> Runnable[RedboxState, dict[str, Any]]:
    """Returns a Runnable that uses state["request"] and state["documents"] to set state["text"].

    If tools are supplied, can also set state["tool_calls"].
    """

    @RunnableLambda
    def _stuff(state: RedboxState) -> dict[str, Any]:
        llm = get_chat_llm(state["request"].ai_settings.chat_backend, tools=tools)

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


def build_set_self_route_from_llm_answer(
    conditional: Callable[[str], bool],
    true_condition_state_update: dict,
    false_condition_state_update: dict,
    final_route_response: bool = True,
) -> Runnable[RedboxState, dict[str, Any]]:
    """A Runnable which sets the route based on a conditional on state['text']"""

    @RunnableLambda
    def _set_self_route_from_llm_answer(state: RedboxState):
        llm_response = state["messages"][-1].content
        if conditional(llm_response):
            return true_condition_state_update
        else:
            return false_condition_state_update

    runnable = _set_self_route_from_llm_answer
    if final_route_response:
        runnable = _set_self_route_from_llm_answer.with_config(tags=[ROUTE_NAME_TAG])
    return runnable


def build_passthrough_pattern() -> Runnable[RedboxState, dict[str, Any]]:
    """Returns a Runnable that uses state["request"] to set state["text"]."""

    @RunnableLambda
    def _passthrough(state: RedboxState) -> dict[str, Any]:
        return {
            "messages": [HumanMessage(content=state["request"].question)],
        }

    return _passthrough


def build_set_text_pattern(text: str, final_response_chain: bool = False) -> Runnable[RedboxState, dict[str, Any]]:
    """Returns a Runnable that can arbitrarily set state["messages"] to a value."""
    llm = CannedChatLLM(messages=[AIMessage(content=text)])
    _llm = llm.with_config(tags=["response_flag"]) if final_response_chain else llm

    @RunnableLambda
    def _set_text(state: RedboxState) -> dict[str, Any]:
        set_text_chain = _llm | StrOutputParser()

        return {"messages": state.get("messages", []) + [HumanMessage(content=set_text_chain.invoke(text))]}

    return _set_text


def build_set_metadata_pattern() -> Runnable[RedboxState, dict[str, Any]]:
    """A Runnable which calculates the static request metadata from the state"""

    @RunnableLambda
    def _set_metadata_pattern(state: RedboxState):
        flat_docs = flatten_document_state(state.get("documents", {}))
        return {
            "metadata": RequestMetadata(
                selected_files_total_tokens=sum(map(lambda d: d.metadata.get("token_count", 0), flat_docs)),
                number_of_selected_files=len(state["request"].s3_keys),
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


def build_tool_pattern(
    tools=list[StructuredTool], final_source_chain: bool = False
) -> Runnable[RedboxState, dict[str, Any]]:
    """Builds a process that takes state["tool_calls"] and returns state updates.

    The state attributes affected are defined in the tool.
    """
    tools_by_name: dict[str, StructuredTool] = {}

    for tool in tools:
        if not is_valid_tool(tool):
            msg = f"{tool.name} must use a function that returns a correctly-formatted RedboxState update"
            raise ValueError(msg)
        tools_by_name[tool.name] = tool

    @RunnableLambda
    def _tool(state: RedboxState) -> dict[str, Any]:
        state_updates: list[dict] = []

        tool_calls = state.get("tool_calls", {})
        if not tool_calls:
            log.warning("No tool calls found in state")
            return {}

        for tool_id, tool_call_dict in tool_calls.items():
            tool_call = tool_call_dict["tool"]

            if not tool_call_dict["called"]:
                tool = tools_by_name[tool_call["name"]]

                if tool is None:
                    log.warning(f"Tool {tool_call['name']} not found")
                    continue

                # Deal with InjectedState
                args = tool_call["args"].copy()
                log.info(f"Invoking tool {tool_call['name']} with args {args}")
                if has_injected_state(tool):
                    args["state"] = state

                # Invoke the tool
                try:
                    result_state_update = tool.invoke(args) or {}
                    log_activity(
                        get_log_formatter_for_retrieval_tool(tool_call).log_result(
                            flatten_document_state(result_state_update.get("documents"))
                        )
                    )
                    tool_called_state_update = {"tool_calls": {tool_id: {"called": True, "tool": tool_call}}}
                    state_updates.append(result_state_update | tool_called_state_update)
                except Exception as e:
                    state_updates.append({"tool_calls": {tool_id: {"called": True, "tool": tool_call}}})
                    log.warning(f"Error invoking tool {tool_call['name']}: {e} \n")
                    return {}

        if state_updates:
            return reduce(merge_redbox_state_updates, state_updates)

    if final_source_chain:
        return RunnableLambda(_tool).with_config(tags=[SOURCE_DOCUMENTS_TAG])

    return _tool


# Raw processes: functions that need no building


def clear_documents_process(state: RedboxState) -> dict[str, Any]:
    if documents := state.get("documents"):
        return {"documents": {group_id: None for group_id in documents}}


def report_sources_process(state: RedboxState) -> None:
    """A Runnable which reports the documents in the state as sources."""
    if citations_state := state.get("citations"):
        dispatch_custom_event(RedboxEventType.on_citations_report, citations_state)
    elif document_state := state.get("documents"):
        dispatch_custom_event(RedboxEventType.on_source_report, flatten_document_state(document_state))


def empty_process(state: RedboxState) -> None:
    return None


def build_log_node(message: str) -> Runnable[RedboxState, dict[str, Any]]:
    """A Runnable which logs the current state in a compact way"""

    @RunnableLambda
    def _log_node(state: RedboxState):
        log.info(
            json.dumps(
                {
                    "user_uuid": str(state["request"].user_uuid),
                    "document_metadata": {
                        group_id: {doc_id: d.metadata for doc_id, d in group_documents.items()}
                        for group_id, group_documents in state["documents"]
                    },
                    "messages": (textwrap.shorten(state["messages"][-1].content, width=32, placeholder="...")),
                    "route": state["route_name"],
                    "message": message,
                }
            )
        )
        return None

    return _log_node


def build_activity_log_node(
    log_message: RedboxActivityEvent
    | Callable[[RedboxState], Iterable[RedboxActivityEvent]]
    | Callable[[RedboxState], Iterable[RedboxActivityEvent]],
):
    """
    A Runnable which emits activity events based on the state. The message should either be a static message to log, or a function which returns an activity event or an iterator of them
    """

    @RunnableLambda
    def _activity_log_node(state: RedboxState):
        if isinstance(log_message, RedboxActivityEvent):
            log_activity(log_message)
        else:
            response = log_message(state)
            if isinstance(response, RedboxActivityEvent):
                log_activity(response)
            else:
                for message in response:
                    log_activity(message)
        return None

    return _activity_log_node
