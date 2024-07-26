import logging

from langchain.schema import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableLambda, RunnableParallel, chain
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_text_splitters import TextSplitter
from langgraph.constants import Send
from tiktoken import Encoding

from redbox.api.format import format_documents
from redbox.models import ChatRoute, Settings
from redbox.models.chain import ChainState, ChatMapReduceState, ChatState
from redbox.models.errors import QuestionLengthError

log = logging.getLogger()


def build_get_chat_docs(
    env: Settings,
    retriever: VectorStoreRetriever
):
    return RunnableParallel({
        "documents": retriever
    })


@chain
def set_route(state: ChainState):
    """
    Choose an approach to chatting based on the current state
    """
    log.debug(f"Choosing how to include docs")
    if len(state["query"].file_uuids) > 0:
        selected = ChatRoute.chat_with_docs.value
    else:
        selected = ChatRoute.chat.value
    log.info(f"Based on user query [{selected}] selected")
    return {
        "route_name": selected
    }

@chain
def set_chat_method(state: ChatState):
    """
    Choose an approach to chatting based on the current state
    """
    log.debug(f"Selecting chat method")
    number_of_docs = len(state["documents"])
    if number_of_docs == 0:
        selected_tool = ChatRoute.chat
    elif number_of_docs == 1:
        selected_tool = ChatRoute.chat_with_docs
    else:
        selected_tool = ChatRoute.chat_with_docs_map_reduce
    log.info(f"Selected: {selected_tool} for execution")
    return {
        "route_name": selected_tool
    }


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
        log.debug(f"Setting chat prompt")
        chat_history_budget = token_budget - len(tokeniser.encode(state["query"].question))

        if chat_history_budget <= 0:
            raise QuestionLengthError

        truncated_history: list[dict[str, str]] = []
        for msg in state["query"].chat_history[::-1]:
            chat_history_budget -= len(tokeniser.encode(msg["text"]))
            if chat_history_budget <= 0:
                break
            else:
                truncated_history.insert(0, msg)

        return ChatPromptTemplate.from_messages(
            system_prompt_message
            + [(msg["role"], msg["text"]) for msg in truncated_history]
            + [("user", question_prompt)]
        ).invoke(state["query"].dict() | state.get("prompt_args", {}))

    return chat_prompt_from_messages

@chain
def set_chat_prompt_args(state: ChatState):
    log.debug(f"Setting prompt args")
    return {
        "prompt_args": {
            "formatted_documents": format_documents(state.get("documents") or []),
        }
    }


def build_llm_chain(
    llm: BaseChatModel,
    tokeniser: Encoding,
    env: Settings,
    system_prompt: str,
    question_prompt: str
) -> Runnable:
    return RunnableParallel({
        "response": make_chat_prompt_from_messages_runnable(
                system_prompt=system_prompt,
                question_prompt=question_prompt,
                input_token_budget=env.ai.context_window_size - env.llm_max_tokens,
                tokeniser=tokeniser,
            )
            | llm.with_config(tags=["response"])
            | StrOutputParser(),
    })


def build_llm_map_chain(
    llm: BaseChatModel,
    tokeniser: Encoding,
    env: Settings,
    system_prompt: str,
    question_prompt: str
) -> Runnable:
    
    return (
        make_chat_prompt_from_messages_runnable(
            system_prompt=system_prompt,
            question_prompt=question_prompt,
            input_token_budget=env.ai.context_window_size - env.llm_max_tokens,
            tokeniser=tokeniser,
        )
        | llm
        | StrOutputParser()
        | RunnableLambda(lambda s: {"intermediate_docs": [Document(page_content=s)]})
    )


@chain
def to_map_step(state: ChatMapReduceState):
    """
    Map each doc in the state to an execution of the llm map step which will create an answer
    per current document
    """
    return [
        Send(
            "llm_map", 
            ChatMapReduceState(
                query=state["query"],
                documents=[doc],
                route_name=state["route_name"],
                prompt_args=state["prompt_args"]
            )
        )
        for doc in state["documents"]
    ]


def build_reduce_docs_step(splitter: TextSplitter):
    return (
        RunnableLambda(lambda state: [Document(page_content=s) for s in splitter.split_text(format_documents(state["intermediate_docs"]))] )
        | RunnableLambda(lambda docs: {"documents": docs})
    )

def empty_node(state: ChainState):
    log.info(f"Empty Node: {state}")
    return None