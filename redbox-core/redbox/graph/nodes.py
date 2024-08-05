import logging
import re
from typing import Any, Callable
from uuid import UUID, uuid4
from functools import reduce

from langchain.schema import StrOutputParser
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableLambda, RunnableParallel, chain
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.vectorstores import VectorStoreRetriever
from tiktoken import Encoding

from redbox.api.format import format_documents
from redbox.api.runnables import filter_by_elbow
from redbox.chains.components import get_tokeniser
from redbox.models import ChatRoute
from redbox.models.chain import ChainChatMessage, RedboxState
from redbox.models.errors import QuestionLengthError
from redbox.transform import combine_documents, structure_documents
from redbox.models.chain import PromptSet, get_prompts


log = logging.getLogger()
re_keyword_pattern = re.compile(r"@(\w+)")


def build_get_docs(retriever: VectorStoreRetriever):
    return RunnableParallel({"documents": retriever | structure_documents})


def build_get_docs_with_filter(retriever: VectorStoreRetriever):
    @chain
    def _build_get_docs_with_filter(state: RedboxState):
        return RunnableParallel(
            {"documents": retriever | filter_by_elbow(state["request"].ai_settings.elbow_filter_enabled) | structure_documents}
        )

    return _build_get_docs_with_filter


@chain
def set_route(state: RedboxState):
    """
    Choose an approach to chatting based on the current state
    """
    # Match keyword
    if route_match := re_keyword_pattern.search(state["request"].question):
        match = route_match.group()[1:]
        try:
            if ChatRoute(match):
                selected = match
        except ValueError:
            selected = ChatRoute.error_no_keyword.value
    elif len(state["request"].file_uuids) > 0:
        selected = ChatRoute.chat_with_docs.value
    else:
        selected = ChatRoute.chat.value
    log.info(f"Based on user query [{selected}] selected")
    return {"route_name": selected}


@chain
def set_chat_method(state: RedboxState):
    """
    Choose an approach to chatting based on the current state
    """
    log.debug("Selecting chat method")
    number_of_docs = len(state["documents"])
    if number_of_docs == 0:
        selected_tool = ChatRoute.chat
    elif number_of_docs == 1:
        selected_tool = ChatRoute.chat_with_docs
    else:
        selected_tool = ChatRoute.chat_with_docs_map_reduce
    log.info(f"Selected: {selected_tool} for execution")
    return {"route_name": selected_tool}


def make_chat_prompt_from_messages_runnable(prompt_set: PromptSet, tokeniser: Encoding = None):
    @chain
    def chat_prompt_from_messages(state: RedboxState):
        """
        Create a ChatPromptTemplate as part of a chain using 'chat_history'.
        Returns the PromptValue using values in the input_dict
        """
        _tokeniser = tokeniser or get_tokeniser()
        system_prompt, question_prompt = get_prompts(state, prompt_set)

        log.debug("Setting chat prompt")
        system_prompt_message = [("system", system_prompt)]
        prompts_budget = len(_tokeniser.encode(system_prompt)) + len(_tokeniser.encode(question_prompt))
        chat_history_budget = state["request"].ai_settings.context_window_size - state["request"].ai_settings.llm_max_tokens - prompts_budget

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
            "text": state.get("text")
        }

        return ChatPromptTemplate.from_messages(
            system_prompt_message
            + [(msg["role"], msg["text"]) for msg in truncated_history]
            + [("user", question_prompt)]
        ).invoke(prompt_template_context)

    return chat_prompt_from_messages


def build_llm_chain(
    llm: BaseChatModel,
    prompt_set: PromptSet,
    final_response_chain=False,
) -> Runnable:
    _llm = llm.with_config(tags=["response_flag"]) if final_response_chain else llm
    return (
        make_chat_prompt_from_messages_runnable(prompt_set)
        | _llm
        | {"text": StrOutputParser()}
    )


def build_merge_pattern(
    llm: BaseChatModel,
    prompt_set: PromptSet,
    final_response_chain=False,
) -> Callable[[RedboxState], dict[str, Any]]:
    @chain
    def wrapped(state: RedboxState):
        _llm = llm.with_config(tags=["response_flag"]) if final_response_chain else llm
        tokeniser = get_tokeniser()

        flattened_documents = flatten_document_state(state["documents"])
        merged_document = reduce(lambda l, r: combine_documents(l, r), flattened_documents)
        merged_document.page_content = build_llm_chain(_llm, prompt_set).invoke(
            RedboxState(
                request=state["request"],
                documents={merged_document.metadata["parent_file_uuid"]: {merged_document.metadata["uuid"]: merged_document}}
            )
        )["text"]

        merged_document.metadata["token_count"] = len(
            tokeniser.encode(merged_document.page_content)
        )
        group_uuid = merged_document.metadata.get("parent_file_uuid", uuid4())
        document_uuid = merged_document.metadata.get("uuid", uuid4())

        # Clear old documents, add new one
        document_state = state["documents"].copy()
        
        for group in document_state:
            for document in document_state[group]:
                document_state[group][document] = None
        
        document_state[group_uuid][document_uuid] = merged_document
        
        return {
            "documents": document_state
        }
    return wrapped


def flatten_document_state(documents: dict[UUID, dict[UUID, Document]]) -> list[Document]:
    if not documents:
        return []
    return [
        document
        for group in documents.values()
        for document in group.values()
    ]


def make_passthrough_pattern() -> Callable[[RedboxState], dict[str, Any]]:
    """Returns a function that uses state["request"] to set state["text"]."""
    def _passthrough(state: RedboxState) -> dict[str, Any]:
        return {
            "text": state["request"]["question"],
        }
    
    return _passthrough


def set_state_field(state_field: str, value: Any):
    return RunnableLambda(
        lambda _: {
            state_field: value,
        }
    )


def empty_node(state: RedboxState):
    return None
