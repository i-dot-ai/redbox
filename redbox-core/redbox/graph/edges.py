import logging
import re
from typing import Literal

from langchain_core.runnables import Runnable

from redbox.chains.components import get_tokeniser
from redbox.graph.nodes.processes import PromptSet
from redbox.models import ChatRoute
from redbox.models.chain import RedboxState, get_prompts
from redbox.transform import get_document_token_count

log = logging.getLogger()


def calculate_token_budget(state: RedboxState, system_prompt: str, question_prompt: str) -> int:
    tokeniser = get_tokeniser()

    len_question_prompt = len(tokeniser.encode(question_prompt))
    len_system_prompt = len(tokeniser.encode(system_prompt))

    ai_settings = state["request"].ai_settings

    return ai_settings.context_window_size - ai_settings.llm_max_tokens - len_system_prompt - len_question_prompt


def build_total_tokens_request_handler_conditional(prompt_set: PromptSet) -> Runnable:
    """Uses a set of prompts to calculate the total tokens used in this request and returns a label
    for the request handler to be used
    """

    def _total_tokens_request_handler_conditional(
        state: RedboxState,
    ) -> Literal["max_exceeded", "context_exceeded", "pass"]:
        system_prompt, question_prompt = get_prompts(state, prompt_set)
        token_budget_remaining_in_context = calculate_token_budget(state, system_prompt, question_prompt)
        max_tokens_allowed = state["request"].ai_settings.max_document_tokens

        total_tokens = state["metadata"].selected_files_total_tokens

        if total_tokens > max_tokens_allowed:
            return "max_exceeded"
        elif total_tokens > token_budget_remaining_in_context:
            return "context_exceeded"
        else:
            return "pass"

    return _total_tokens_request_handler_conditional


def build_documents_bigger_than_context_conditional(prompt_set: PromptSet) -> Runnable:
    """Uses a set of prompts to build the correct conditional for exceeding the context window."""

    def _documents_bigger_than_context_conditional(state: RedboxState) -> bool:
        system_prompt, question_prompt = get_prompts(state, prompt_set)
        token_budget = calculate_token_budget(state, system_prompt, question_prompt)

        return get_document_token_count(state) > token_budget

    return _documents_bigger_than_context_conditional


def documents_bigger_than_n_conditional(state: RedboxState) -> bool:
    """Do the documents meet a hard limit of document token size set in AI Settings."""
    token_counts = get_document_token_count(state)
    return sum(token_counts) > state["request"].ai_settings.max_document_tokens


def build_keyword_detection_conditional(*allowed_routes: ChatRoute) -> Runnable:
    """Given a set of permitted routes, will detect them in keywords."""

    def _keyword_detection_conditional(state: RedboxState) -> ChatRoute | str:
        re_keyword_pattern = re.compile(r"@(\w+)")

        route_match = re_keyword_pattern.search(state["request"].question)
        route_name = route_match.group()[1:] if route_match else None

        try:
            route = ChatRoute[route_name]
            if route in allowed_routes:
                return route
        except KeyError:
            if route_name is not None:
                return "DEFAULT"

        return "DEFAULT"

    return _keyword_detection_conditional


def documents_selected_conditional(state: RedboxState) -> bool:
    return len(state["request"].s3_keys) > 0


def multiple_docs_in_group_conditional(state: RedboxState) -> bool:
    return any(len(group) > 1 for group in state.get("documents", {}).values())


def build_tools_selected_conditional(tools: list[str]) -> Runnable:
    """Given a list of tools, returns True if any tool is in the state and uncalled."""

    def _tools_selected_conditional(state: RedboxState) -> bool:
        for tool_call in state["tool_calls"].values():
            if tool_call["tool"]["name"] in tools and not tool_call["called"]:
                return True
        return False

    return _tools_selected_conditional


def build_strings_end_text_conditional(*strings: str) -> Runnable:
    """Given a list of strings, returns the string if the end of state["text"] contains it."""
    pattern = "|".join(re.escape(s) for s in strings)
    regex = re.compile(pattern, re.IGNORECASE)

    def _strings_end_text_conditional(state: RedboxState) -> str:
        matches = regex.findall(state["text"][-100:])  # padding for waffle
        unique_matches = set(matches)

        if len(unique_matches) == 1:
            return unique_matches.pop().lower()
        return "DEFAULT"

    return _strings_end_text_conditional
