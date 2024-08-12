import logging
from typing import Any, Iterator

from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.language_models.llms import LLM
from langchain_core.outputs import GenerationChunk
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, chain
from tiktoken import Encoding

from redbox.api.format import format_documents
from redbox.chains.components import get_tokeniser
from redbox.models.chain import ChainChatMessage, RedboxState
from redbox.models.errors import QuestionLengthError
from redbox.models.chain import PromptSet, get_prompts
from redbox.transform import flatten_document_state


log = logging.getLogger()


def build_chat_prompt_from_messages_runnable(prompt_set: PromptSet, tokeniser: Encoding = None):
    @chain
    def _chat_prompt_from_messages(state: RedboxState) -> Runnable:
        """
        Create a ChatPromptTemplate as part of a chain using 'chat_history'.
        Returns the PromptValue using values in the input_dict
        """
        _tokeniser = tokeniser or get_tokeniser()
        system_prompt, question_prompt = get_prompts(state, prompt_set)

        log.debug("Setting chat prompt")
        system_prompt_message = [("system", system_prompt)]
        prompts_budget = len(_tokeniser.encode(system_prompt)) + len(_tokeniser.encode(question_prompt))
        chat_history_budget = (
            state["request"].ai_settings.context_window_size
            - state["request"].ai_settings.llm_max_tokens
            - prompts_budget
        )

        if chat_history_budget <= 0:
            raise QuestionLengthError

        truncated_history: list[ChainChatMessage] = []
        for msg in state["request"].chat_history[::-1]:
            chat_history_budget -= len(tokeniser.encode(msg["text"]))
            if chat_history_budget <= 0:
                break
            else:
                truncated_history.insert(0, msg)

        prompt_template_context = state["request"].model_dump() | {
            "formatted_documents": format_documents(flatten_document_state(state["documents"])),
        }

        return ChatPromptTemplate.from_messages(
            system_prompt_message
            + [(msg["role"], msg["text"]) for msg in truncated_history]
            + [("user", question_prompt)]
        ).invoke(prompt_template_context)

    return _chat_prompt_from_messages


class CannedLLM(LLM):
    """A custom chat model that returns its text as if an LLM returned it."""

    text: str

    def _call(
        self,
        prompt: str,
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> str:
        """Run the LLM on the given input.

        Args:
            prompt: The prompt to generate from.
            stop: Stop words to use when generating. Model output is cut off at the
                first occurrence of any of the stop substrings.
                If stop tokens are not supported consider raising NotImplementedError.
            run_manager: Callback manager for the run.
            **kwargs: Arbitrary additional keyword arguments. These are usually passed
                to the model provider API call.

        Returns:
            The model output as a string. Actual completions SHOULD NOT include the prompt.
        """
        if stop is not None:
            raise ValueError("stop kwargs are not permitted.")
        return self.text

    def _stream(
        self,
        prompt: str,
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> Iterator[GenerationChunk]:
        """Stream the LLM on the given prompt.

        Args:
            prompt: The prompt to generate from.
            stop: Stop words to use when generating. Model output is cut off at the
                first occurrence of any of these substrings.
            run_manager: Callback manager for the run.
            **kwargs: Arbitrary additional keyword arguments. These are usually passed
                to the model provider API call.

        Returns:
            An iterator of GenerationChunks.
        """
        for char in self.text.split():
            chunk = GenerationChunk(text=char)
            if run_manager:
                run_manager.on_llm_new_token(chunk.text, chunk=chunk)

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
