import logging
import re
from operator import itemgetter
from typing import Any, Callable, Iterable, Iterator

from langchain_core.callbacks.manager import CallbackManagerForLLMRun, dispatch_custom_event
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableGenerator, RunnableLambda, chain
from tiktoken import Encoding

from redbox.api.format import format_documents, format_toolstate
from redbox.chains.components import get_tokeniser
from redbox.models.chain import ChainChatMessage, PromptSet, RedboxState, get_prompts
from redbox.models.errors import QuestionLengthError
from redbox.models.graph import RedboxEventType
from redbox.transform import (
    flatten_document_state,
    to_request_metadata,
    tool_calls_to_toolstate,
)

log = logging.getLogger()
re_string_pattern = re.compile(r"(\S+)")


def combine_getters(*getters: Callable[[Any], Any]) -> Callable[[Any], Any]:
    """Permits chaining of *getter functions in LangChain."""

    def _combined(obj):
        for getter in getters:
            obj = getter(obj)
        return obj

    return _combined


def build_chat_prompt_from_messages_runnable(prompt_set: PromptSet, tokeniser: Encoding = None) -> Runnable:
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
            chat_history_budget -= len(_tokeniser.encode(msg["text"]))
            if chat_history_budget <= 0:
                break
            else:
                truncated_history.insert(0, msg)

        prompt_template_context = (
            state["request"].model_dump()
            | {"text": state.get("text")}
            | {
                "formatted_documents": format_documents(flatten_document_state(state.get("documents"))),
            }
            | {"tool_calls": format_toolstate(state.get("tool_calls"))}
        )

        return ChatPromptTemplate.from_messages(
            system_prompt_message
            + [(msg["role"], msg["text"]) for msg in truncated_history]
            + [("user", question_prompt)]
        ).invoke(prompt_template_context)

    return _chat_prompt_from_messages


def build_llm_chain(
    prompt_set: PromptSet,
    llm: BaseChatModel,
    output_parser: Runnable | Callable = None,
    final_response_chain: bool = False,
) -> Runnable:
    """Builds a chain that correctly forms a text and metadata state update.

    Permits both invoke and astream_events.
    """
    model_name = getattr(llm, "model_name", "unknown-model")
    _llm = llm.with_config(tags=["response_flag"]) if final_response_chain else llm
    _output_parser = output_parser if output_parser else StrOutputParser()

    return (
        build_chat_prompt_from_messages_runnable(prompt_set)
        | {
            "text_and_tools": (
                _llm
                | {
                    "text": _output_parser,
                    "tool_calls": (RunnableLambda(lambda r: r.tool_calls) | tool_calls_to_toolstate),
                }
            ),
            "prompt": RunnableLambda(lambda prompt: prompt.to_string()),
        }
        | {
            "text": combine_getters(itemgetter("text_and_tools"), itemgetter("text")),
            "tool_calls": combine_getters(itemgetter("text_and_tools"), itemgetter("tool_calls")),
            "metadata": (
                {
                    "prompt": itemgetter("prompt"),
                    "response": combine_getters(itemgetter("text_and_tools"), itemgetter("text")),
                    "model": lambda _: model_name,
                }
                | to_request_metadata
            ),
        }
    )


def build_self_route_output_parser(
    match_condition: Callable[[str], bool], max_tokens_to_check: int, final_response_chain: bool = False
) -> Runnable[Iterable[AIMessageChunk], Iterable[str]]:
    """
    This Runnable reads the streamed responses from an LLM until the match
    condition is true for the response so far it has read a number of tokens.
    If the match condition is true it breaks off and returns nothing to the
    client, if not then it streams the response to the client as normal.

    Used to handle responses from prompts like 'If this question can be
    answered answer it, else return False'
    """

    def _self_route_output_parser(chunks: Iterable[AIMessageChunk]) -> Iterable[str]:
        current_content = ""
        token_count = 0
        for chunk in chunks:
            current_content += chunk.content
            token_count += 1
            if match_condition(current_content):
                yield current_content
                return
            elif token_count > max_tokens_to_check:
                break
        if final_response_chain:
            dispatch_custom_event(RedboxEventType.response_tokens, current_content)
        yield current_content
        for chunk in chunks:
            if final_response_chain:
                dispatch_custom_event(RedboxEventType.response_tokens, chunk.content)
            yield chunk.content

    return RunnableGenerator(_self_route_output_parser)


class CannedChatLLM(BaseChatModel):
    """A custom chat model that returns its text as if an LLM returned it.

    Based on https://python.langchain.com/v0.2/docs/how_to/custom_chat_model/
    """

    text: str

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
        message = AIMessage(content=self.text)

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
        for token in re_string_pattern.split(self.text):
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
