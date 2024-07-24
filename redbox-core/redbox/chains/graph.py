import logging
import sys
from operator import itemgetter

from langchain.prompts import PromptTemplate
from langchain.schema import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import Runnable, RunnableLambda, RunnablePassthrough, chain, RunnableConfig
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import tool
from langchain_core.vectorstores import VectorStoreRetriever
from regex import P
from tiktoken import Encoding

from redbox.api.format import format_documents
from redbox.api.runnables import resize_documents
from redbox.models import ChatRoute, Settings
from redbox.models.chat import ChatResponse
from redbox.models.chain import ChainState, ChatState
from redbox.retriever.retrievers import AllElasticsearchRetriever
from redbox.models.errors import NoDocumentSelected, QuestionLengthError
from redbox.transform import map_document_to_source_document


logging.basicConfig(stream=sys.stdout, level=logging.INFO)
log = logging.getLogger()


def build_get_chat_docs(
    env: Settings,
    retriever: VectorStoreRetriever
):
    return {
        "documents": retriever | resize_documents(env.ai.summarisation_chunk_max_tokens)
    }


@chain
def chat_include_docs_decision(state: ChainState):
    """
    Choose an approach to chatting based on the current state
    """
    if len(state.query.file_uuids) > 0:
        selected = ChatRoute.chat_with_docs
    else:
        selected = ChatRoute.chat
    log.info(f"Based on user query [{selected}] selected")
    return selected

@chain
def chat_method_decision(state: ChatState):
    """
    Choose an approach to chatting based on the current state
    """
    number_of_docs = len(state.documents)
    if number_of_docs == 0:
        selected_tool = ChatRoute.chat
    elif number_of_docs == 1:
        selected_tool = ChatRoute.chat_with_docs
    else:
        selected_tool = ChatRoute.chat_with_docs_map_reduce
    log.info(f"Selected: {selected_tool} for execution")
    return selected_tool


def make_chat_prompt_from_messages_runnable(
    system_prompt: str,
    question_prompt: str,
    input_token_budget: int,
    tokeniser: Encoding,
):
    system_prompt_message = [("system", system_prompt)]
    prompts_budget = len(tokeniser.encode(system_prompt)) - len(tokeniser.encode(question_prompt))
    token_budget = input_token_budget - prompts_budget

    @chain
    def chat_prompt_from_messages(state: ChatState):
        """
        Create a ChatPrompTemplate as part of a chain using 'chat_history'.
        Returns the PromptValue using values in the input_dict
        """
        chat_history_budget = token_budget - len(tokeniser.encode(state.query.question))

        if chat_history_budget <= 0:
            raise QuestionLengthError

        truncated_history: list[dict[str, str]] = []
        for msg in state.query.chat_history[::-1]:
            chat_history_budget -= len(tokeniser.encode(msg["text"]))
            if chat_history_budget <= 0:
                break
            else:
                truncated_history.insert(0, msg)

        return ChatPromptTemplate.from_messages(
            system_prompt_message
            + [(msg["role"], msg["text"]) for msg in truncated_history]
            + [("user", question_prompt)]
        ).invoke(state.query.dict() | state.prompt_args)

    return chat_prompt_from_messages

@chain
def set_chat_prompt_args(state: ChainState):
    return {
        "prompt_args": {
            "formatted_documents": format_documents(state.documents),
            "question": state.query.question,
            "chat_history": state.query.chat_history
        }
    }
    

def build_chat_chain(
    llm: BaseChatModel,
    tokeniser: Encoding,
    env: Settings
) -> Runnable:
    return (
        make_chat_prompt_from_messages_runnable(
            system_prompt=env.ai.chat_system_prompt,
            question_prompt=env.ai.chat_question_prompt,
            input_token_budget=env.ai.context_window_size - env.llm_max_tokens,
            tokeniser=tokeniser,
        )
        | llm
        | {
            "response": StrOutputParser(),
            "route_name": RunnableLambda(lambda _: ChatRoute.chat.value),
        }
    )


def build_chat_with_docs_chain(
    llm: BaseChatModel,
    tokeniser: Encoding,
    env: Settings
):
    return {
        "response": make_chat_prompt_from_messages_runnable(
                system_prompt=env.ai.chat_with_docs_system_prompt,
                question_prompt=env.ai.chat_with_docs_question_prompt,
                input_token_budget=env.ai.context_window_size - env.llm_max_tokens,
                tokeniser=tokeniser,
            )
            | llm
            | StrOutputParser(),
        "route_name": RunnableLambda(lambda _: ChatRoute.chat_with_docs.value),
    }
    
def build_chat_with_docs_map_reduce_chain():
    return RunnableLambda(lambda state: {
        "response": f"Max content exceeded. Try smaller or fewer documents",
        "route_name": ChatRoute.chat_with_docs_map_reduce.value,
    })


def empty_node(state: ChainState):
    log.info(f"Empty Node: {state}")
    return None