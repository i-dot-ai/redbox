import logging
from typing import Literal

from langchain_core.runnables import Runnable

from redbox.chains.components import get_tokeniser
from redbox.graph.nodes.processes import PromptSet
from redbox.models.chain import RedboxState, get_prompts

log = logging.getLogger()


def calculate_token_budget(state: RedboxState, system_prompt: str, question_prompt: str) -> int:
    tokeniser = get_tokeniser()

    len_question_prompt = len(tokeniser.encode(question_prompt))
    len_system_prompt = len(tokeniser.encode(system_prompt))

    ai_settings = state.request.ai_settings

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
        max_tokens_allowed = state.request.ai_settings.max_document_tokens

        total_tokens = sum(x.metadata["token_count"] for x in state.request.documents)

        if total_tokens > max_tokens_allowed:
            return "max_exceeded"
        elif total_tokens > token_budget_remaining_in_context:
            return "max_exceeded"
        else:
            return "pass"

    return _total_tokens_request_handler_conditional


def documents_selected_conditional(state: RedboxState) -> bool:
    return len(state.request.s3_keys) > 0
