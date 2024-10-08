from typing import Callable

from langgraph.constants import Send

from redbox.models.chain import RedboxState


def _copy_state(state: RedboxState, **updates) -> RedboxState:
    kwargs = dict(state) | updates
    return RedboxState(**kwargs)


def build_document_group_send(target: str) -> Callable[[RedboxState], list[Send]]:
    """Builds Sends per document group."""

    def _group_send(state: RedboxState) -> list[Send]:
        group_send_states: list[RedboxState] = [
            _copy_state(
                state,
                documents={document_group_key: document_group},
            )
            for document_group_key, document_group in state["documents"].items()
        ]
        return [Send(node=target, arg=state) for state in group_send_states]

    return _group_send


def build_document_chunk_send(target: str) -> Callable[[RedboxState], list[Send]]:
    """Builds Sends per individual document"""

    def _chunk_send(state: RedboxState) -> list[Send]:
        chunk_send_states: list[RedboxState] = [
            _copy_state(
                state,
                documents={document_group_key: {document_key: document}},
            )
            for document_group_key, document_group in state["documents"].items()
            for document_key, document in document_group.items()
        ]
        return [Send(node=target, arg=state) for state in chunk_send_states]

    return _chunk_send


def build_tool_send(target: str) -> Callable[[RedboxState], list[Send]]:
    """Builds Sends per tool call."""

    def _tool_send(state: RedboxState) -> list[Send]:
        tool_send_states: list[RedboxState] = [
            _copy_state(
                state,
                tool_calls={tool_id: tool_call},
            )
            for tool_id, tool_call in state["tool_calls"].items()
        ]
        return [Send(node=target, arg=state) for state in tool_send_states]

    return _tool_send
