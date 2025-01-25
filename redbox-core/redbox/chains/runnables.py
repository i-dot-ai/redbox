from langchain_core.runnables import (
    Runnable,
    chain,
)
from langchain_core.prompts import ChatPromptTemplate

from redbox.chains.components import get_tokeniser
from redbox.models.chain import ChainChatMessage, RedboxState
from redbox.api.format import format_documents


def build_chat_prompt_from_messages_runnable() -> Runnable:
    @chain
    def _chat_prompt_from_messages(state: RedboxState) -> Runnable:
        """
        Create a ChatPromptTemplate as part of a chain using 'chat_history'.
        Returns the PromptValue using values in the input_dict
        """
        ai_settings = state.ai_settings
        _tokeniser = get_tokeniser()

        # Set the system prompt to be our composed structure
        # We preserve the format instructions
        system_prompt_message = f"""
            {ai_settings.system_info_prompt}
            {ai_settings.chat_with_docs_system_prompt}
            {ai_settings.persona_info_prompt}
            {ai_settings.caller_info_prompt}
            """

        prompts_budget = len(_tokeniser.encode(system_prompt_message))
        chat_history_budget = ai_settings.context_window_size - ai_settings.llm_max_tokens - prompts_budget

        truncated_history: list[ChainChatMessage] = []
        for msg in state.messages:
            chat_history_budget -= len(_tokeniser.encode(msg["text"]))
            if chat_history_budget <= 0:
                break
            else:
                truncated_history.insert(0, msg)

        prompt_template_context = state.model_dump() | {"formatted_documents": format_documents(state.documents)}

        return ChatPromptTemplate(
            messages=([("system", system_prompt_message)] + [(msg["role"], msg["text"]) for msg in truncated_history]),
        ).invoke(prompt_template_context)

    return _chat_prompt_from_messages
