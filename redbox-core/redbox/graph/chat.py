
from langgraph.graph import StateGraph, START
from langgraph.graph.graph import CompiledGraph
from langchain_core.language_models.chat_models import BaseChatModel
from tiktoken import Encoding

from redbox.chains.graph import *
from redbox.models.chain import ChatState
from redbox.models.settings import Settings


def get_chat_graph(
    llm: BaseChatModel,
    all_chunks_retriever: VectorStoreRetriever,
    tokeniser: Encoding,
    env: Settings
) -> CompiledGraph:

    app = StateGraph(ChatState)
    app.add_edge(START, "set_chat_prompt_args")

    app.add_node("set_chat_prompt_args", set_chat_prompt_args)
    app.add_edge("set_chat_prompt_args", "llm")

    app.add_node("llm", build_chat_chain(llm, tokeniser, env))

    return app.compile()


@chain
def no_docs_available(state: ChainState):
    return {
        "response": ChatResponse(
            output_text=f"No available data for selected files. They may need to be removed and added again",
            route_name=state.route_name
        ) 
    }


def get_chat_with_docs_graph(
    llm: BaseChatModel,
    all_chunks_retriever: VectorStoreRetriever,
    tokeniser: Encoding,
    env: Settings
) -> CompiledGraph:

    app = StateGraph(ChatState)

    app.add_edge(START, "get_chat_docs")
    app.add_node("get_chat_docs", build_get_chat_docs(env, all_chunks_retriever))
    app.add_conditional_edges("get_chat_docs", chat_method_decision, {
        ChatRoute.chat: "no_docs_available",
        ChatRoute.chat_with_docs: ChatRoute.chat_with_docs,
        ChatRoute.chat_with_docs_map_reduce: ChatRoute.chat_with_docs_map_reduce
    })

    app.add_node("no_docs_available", no_docs_available)
    app.add_node(ChatRoute.chat_with_docs, build_chat_with_docs_chain(llm, tokeniser, env))
    app.add_node(ChatRoute.chat_with_docs_map_reduce, build_chat_with_docs_map_reduce_chain())

    return app.compile()