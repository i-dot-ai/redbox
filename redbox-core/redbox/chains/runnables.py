import logging
import re

from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import (
    Runnable,
    chain,
)
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tiktoken import Encoding

from redbox.chains.components import get_tokeniser
from redbox.models.chain import ChainChatMessage, PromptSet, RedboxState, get_prompts
from redbox.api.format import format_documents

log = logging.getLogger()
re_string_pattern = re.compile(r"(\S+)")


def build_chat_prompt_from_messages_runnable(
    prompt_set: PromptSet,
    tokeniser: Encoding = None,
    format_instructions: str = "",
) -> Runnable:
    @chain
    def _chat_prompt_from_messages(state: RedboxState) -> Runnable:
        """
        Create a ChatPromptTemplate as part of a chain using 'chat_history'.
        Returns the PromptValue using values in the input_dict
        """
        ai_settings = state.request.ai_settings
        _tokeniser = tokeniser or get_tokeniser()
        task_system_prompt, task_question_prompt = get_prompts(state, prompt_set)

        log.debug("Setting chat prompt")
        # Set the system prompt to be our composed structure
        # We preserve the format instructions
        system_prompt_message = f"""
            {ai_settings.system_info_prompt}
            {task_system_prompt}
            {ai_settings.persona_info_prompt}
            {ai_settings.caller_info_prompt}
            """
        prompts_budget = len(_tokeniser.encode(task_system_prompt)) + len(_tokeniser.encode(task_question_prompt))
        chat_history_budget = ai_settings.context_window_size - ai_settings.llm_max_tokens - prompts_budget

        truncated_history: list[ChainChatMessage] = []
        for msg in state.request.chat_history[::-1]:
            chat_history_budget -= len(_tokeniser.encode(msg["text"]))
            if chat_history_budget <= 0:
                break
            else:
                truncated_history.insert(0, msg)

        prompt_template_context = (
            state.request.model_dump()
            | {
                "formatted_documents": format_documents(state.request.documents)
            }
        )

        return ChatPromptTemplate(
            messages=(
                [("system", system_prompt_message)]
                + [(msg["role"], msg["text"]) for msg in truncated_history]
                + [MessagesPlaceholder("messages")]
                + [task_question_prompt + "\n\n{format_instructions}"]
            ),
            partial_variables={"format_instructions": format_instructions},
        ).invoke(prompt_template_context)

    return _chat_prompt_from_messages


def build_llm_chain(
    prompt_set: PromptSet,
    llm: BaseChatModel,
) -> Runnable:
    """Builds a chain that correctly forms a text and metadata state update.

    Permits both invoke and astream_events.
    """
    return build_chat_prompt_from_messages_runnable(prompt_set) | llm
