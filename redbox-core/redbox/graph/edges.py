import logging
import re
from typing import Callable

from redbox.models.chain import get_prompts
from langgraph.constants import Send

from redbox.chains.components import get_tokeniser
from redbox.graph.nodes import PromptSet
from redbox.models import ChatRoute
from redbox.models.chain import RedboxState
from redbox.transform import flatten_document_state

log = logging.getLogger()


def calculate_token_budget(state: RedboxState, system_prompt: str, question_prompt: str) -> int:
    tokeniser = get_tokeniser()

    len_question_prompt = len(tokeniser.encode(question_prompt))
    len_system_prompt = len(tokeniser.encode(system_prompt))

    ai_settings = state["request"].ai_settings

    return ai_settings.context_window_size - ai_settings.llm_max_tokens - len_system_prompt - len_question_prompt


def build_conditional_documents_bigger_than_context(prompt_set: PromptSet):
    def wrapped(state: RedboxState) -> bool:
        system_prompt, question_prompt = get_prompts(state, prompt_set)
        token_budget = calculate_token_budget(state, system_prompt, question_prompt)

        if sum(d.metadata["token_count"] for d in flatten_document_state(state["documents"])) > token_budget:
            return True
        else:
            return False

    return wrapped


def conditional_keyword_detection(state: RedboxState) -> ChatRoute | None:
    re_keyword_pattern = re.compile(r"@(\w+)")

    route_match = re_keyword_pattern.search(state["request"].question)
    route_name = route_match.group()[1:] if route_match else None

    try:
        return ChatRoute[route_name]
    except KeyError:
        return None


def conditional_documents_selected(state: RedboxState) -> bool:
    return len(state["request"].file_uuids) > 0


def conditional_multiple_docs_in_group(state: RedboxState) -> bool:
    for group in state["documents"]:
        if len(state["documents"][group]) > 0:
            return True
    return False


def make_document_group_send(target: str) -> Callable[[RedboxState], list[Send]]:
    def _group_send(state: RedboxState) -> list[Send]:
        group_send_states: list[RedboxState] = [
            RedboxState(
                request=state["request"],
                text=state.get("text"),
                documents={group_key: state["documents"][group_key]},
                route=state.get("route"),
            )
            for group_key in state["documents"]
        ]
        return [Send(node=target, arg=state) for state in group_send_states]

    return _group_send


def make_document_chunk_send(target: str) -> Callable[[RedboxState], list[Send]]:
    def _chunk_send(state: RedboxState) -> list[Send]:
        chunk_send_states: list[RedboxState] = [
            RedboxState(
                request=state["request"],
                text=state.get("text"),
                documents={group_key: {document_key: state["documents"][group_key][document_key]}},
                route=state.get("route"),
            )
            for group_key in state["documents"]
            for document_key in state["documents"][group_key]
        ]
        return [Send(node=target, arg=state) for state in chunk_send_states]

    return _chunk_send
