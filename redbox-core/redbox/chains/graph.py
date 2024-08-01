import logging
import re
from typing import Any

from langchain.schema import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableLambda, RunnableParallel, chain
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.vectorstores import VectorStoreRetriever
from tiktoken import Encoding

from redbox.api.format import format_documents
from redbox.api.runnables import filter_by_elbow
from redbox.models import ChatRoute
from redbox.models.chain import ChainChatMessage, ChainState, AISettings
from redbox.models.errors import QuestionLengthError

log = logging.getLogger()
re_keyword_pattern = re.compile(r"@(\w+)")


def build_get_docs(retriever: VectorStoreRetriever):
    return RunnableParallel({"documents": retriever})


def build_get_docs_with_filter(ai_settings: AISettings, retriever: VectorStoreRetriever):
    return RunnableParallel({"documents": retriever | filter_by_elbow(ai_settings.elbow_filter_enabled)})


@chain
def set_route(state: ChainState):
    """
    Choose an approach to chatting based on the current state
    """
    # Match keyword
    if route_match := re_keyword_pattern.search(state["query"].question):
        match = route_match.group()[1:]
        try:
            if ChatRoute(match):
                selected = match
        except ValueError:
            selected = ChatRoute.error_no_keyword.value
    elif len(state["query"].file_uuids) > 0:
        selected = ChatRoute.chat_with_docs.value
    else:
        selected = ChatRoute.chat.value
    log.info(f"Based on user query [{selected}] selected")
    return {"route_name": selected}


def make_chat_prompt_from_messages_runnable(
    tokeniser: Encoding,
):
    @chain
    def chat_prompt_from_messages(state: ChainState):
        """
        Create a ChatPromptTemplate as part of a chain using 'chat_history'.
        Returns the PromptValue using values in the input_dict
        """
        log.debug("Setting chat prompt")
        system_prompt_message = [("system", state["query"].ai_settings.chat_system_prompt)]
        prompts_budget = len(tokeniser.encode(state["query"].ai_settings.chat_system_prompt)) - len(
            tokeniser.encode(state["query"].ai_settings.chat_question_prompt)
        )
        token_budget = (
            state["query"].ai_settings.context_window_size - state["query"].ai_settings.llm_max_tokens - prompts_budget
        )
        chat_history_budget = token_budget - len(tokeniser.encode(state["query"].question))

        if chat_history_budget <= 0:
            raise QuestionLengthError

        truncated_history: list[ChainChatMessage] = []
        for msg in state["query"].chat_history[::-1]:
            chat_history_budget -= len(tokeniser.encode(msg["text"]))
            if chat_history_budget <= 0:
                break
            else:
                truncated_history.insert(0, msg)

        return ChatPromptTemplate.from_messages(
            system_prompt_message
            + [(msg["role"], msg["text"]) for msg in truncated_history]
            + [("user", state["query"].ai_settings.chat_question_prompt)]
        ).invoke(state["query"].dict() | state.get("prompt_args", {}))

    return chat_prompt_from_messages


@chain
def set_prompt_args(state: ChainState):
    log.debug("Setting prompt args")
    return {
        "prompt_args": {
            "formatted_documents": format_documents(state.get("documents") or []),
        }
    }


def build_llm_chain(
    llm: BaseChatModel,
    tokeniser: Encoding,
    final_response_chain=False,
) -> Runnable:
    _llm = llm.with_config(tags=["response_flag"]) if final_response_chain else llm
    return RunnableParallel(
        {
            "response": make_chat_prompt_from_messages_runnable(tokeniser=tokeniser) | _llm | StrOutputParser(),
        }
    )


def set_state_field(state_field: str, value: Any):
    return RunnableLambda(
        lambda _: {
            state_field: value,
        }
    )


def empty_node(state: ChainState):
    log.info(f"Empty Node: {state}")
    return None
