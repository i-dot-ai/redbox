import logging
import re
from typing import Any, Iterator

from langchain_core.callbacks.manager import (
    CallbackManagerForLLMRun,
)
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langchain_core.runnables import (
    Runnable,
    RunnableLambda,
    chain,
)
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tiktoken import Encoding

from redbox.chains.components import get_tokeniser
from redbox.models.chain import ChainChatMessage, PromptSet, RedboxState, get_prompts
from redbox.models.errors import QuestionLengthError
from redbox.api.format import format_documents
from redbox.retriever.retrievers import retriever_runnable

log = logging.getLogger()
re_string_pattern = re.compile(r"(\S+)")


def build_chat_prompt_from_messages_runnable(
    prompt_set: PromptSet,
    tokeniser: Encoding = None,
    format_instructions: str = "",
    additional_variables: dict | None = None,
) -> Runnable:
    @chain
    def _chat_prompt_from_messages(state: RedboxState) -> Runnable:
        """
        Create a ChatPromptTemplate as part of a chain using 'chat_history'.
        Returns the PromptValue using values in the input_dict
        """
        ai_settings = state.request.ai_settings
        _tokeniser = tokeniser or get_tokeniser()
        _additional_variables = additional_variables or dict()
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

        if chat_history_budget <= 0:
            raise QuestionLengthError

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
                "messages": state.messages,
                "formatted_documents": format_documents(state.documents),
            }
            | _additional_variables
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
    retriever: Runnable,
    llm: BaseChatModel,
) -> Runnable:
    """Builds a chain that correctly forms a text and metadata state update.

    Permits both invoke and astream_events.
    """
    return (
        RunnableLambda(retriever_runnable(retriever))
        | build_chat_prompt_from_messages_runnable(prompt_set) 
        | llm
    )


class CannedChatLLM(BaseChatModel):
    """A custom chat model that returns its text as if an LLM returned it.

    Based on https://python.langchain.com/v0.2/docs/how_to/custom_chat_model/
    """

    messages: list[AIMessage]

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Run the LLM on the given input.

        Args:
            messages: the prompt composed of a list of messages.
            stop: a list of strings on which the model should stop generating.
                  If generation stops due to a stop token, the stop token itself
                  SHOULD BE INCLUDED as part of the output. This is not enforced
                  across models right now, but it's a good practice to follow since
                  it makes it much easier to parse the output of the model
                  downstream and understand why generation stopped.
            run_manager: A run manager with callbacks for the LLM.
        """
        message = AIMessage(content=self.messages[-1].content)

        generation = ChatGeneration(message=message)
        return ChatResult(generations=[generation])

    def _stream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        """Stream the LLM on the given prompt.

        Args:
            messages: the prompt composed of a list of messages.
            stop: a list of strings on which the model should stop generating.
                  If generation stops due to a stop token, the stop token itself
                  SHOULD BE INCLUDED as part of the output. This is not enforced
                  across models right now, but it's a good practice to follow since
                  it makes it much easier to parse the output of the model
                  downstream and understand why generation stopped.
            run_manager: A run manager with callbacks for the LLM.
        """
        for token in re_string_pattern.split(self.messages[-1].content):
            chunk = ChatGenerationChunk(message=AIMessageChunk(content=token))

            if run_manager:
                # This is optional in newer versions of LangChain
                # The on_llm_new_token will be called automatically
                run_manager.on_llm_new_token(token, chunk=chunk)

            yield chunk

        # Final token should be empty
        chunk = ChatGenerationChunk(message=AIMessageChunk(content=""))
        if run_manager:
            # This is optional in newer versions of LangChain
            # The on_llm_new_token will be called automatically
            run_manager.on_llm_new_token(token, chunk=chunk)

        yield chunk

    @property
    def _identifying_params(self) -> dict[str, Any]:
        """Return a dictionary of identifying parameters."""
        return {
            # The model name allows users to specify custom token counting
            # rules in LLM monitoring applications (e.g., in LangSmith users
            # can provide per token pricing for their model and monitor
            # costs for the given LLM.)
            "model_name": "CannedChatModel",
        }

    @property
    def _llm_type(self) -> str:
        """Get the type of language model used by this chat model. Used for logging purposes only."""
        return "canned"
