
from langgraph.graph import StateGraph, START
from langgraph.constants import Send
from langgraph.graph.graph import CompiledGraph
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_text_splitters import TextSplitter, TokenTextSplitter
from tiktoken import Encoding

from redbox.chains.graph import *
from redbox.models.chain import ChatState
from redbox.models.settings import Settings


def get_chat_graph(
    llm: BaseChatModel,
    tokeniser: Encoding,
    env: Settings,
    debug: bool = False
) -> CompiledGraph:

    app = StateGraph(ChatState)
    app.set_entry_point("set_chat_prompt_args")

    app.add_node("set_chat_prompt_args", set_chat_prompt_args)
    app.add_edge("set_chat_prompt_args", "llm")

    app.add_node("llm", build_llm_chain(llm, tokeniser, env, env.ai.chat_system_prompt, env.ai.chat_question_prompt))

    return app.compile(debug=debug)


def get_no_docs_available(env: Settings):
    return RunnableLambda(lambda _: {
        "response": env.response_no_doc_available,
    })


def get_chat_with_docs_graph(
    llm: BaseChatModel,
    all_chunks_retriever: VectorStoreRetriever,
    tokeniser: Encoding,
    env: Settings,
    debug: bool = False
) -> CompiledGraph:

    app = StateGraph(ChatState)

    app.add_node("get_chat_docs", build_get_chat_docs(env, all_chunks_retriever))
    app.add_node("set_chat_prompt_args", set_chat_prompt_args)
    app.add_node("set_chat_method", set_chat_method)

    app.add_node("no_docs_available", get_no_docs_available(env))
    app.add_node("llm", build_llm_chain(llm, tokeniser, env, env.ai.chat_with_docs_system_prompt, env.ai.chat_with_docs_question_prompt))
    app.add_node(ChatRoute.chat_with_docs_map_reduce, get_chat_with_docs_map_reduce_graph(llm, tokeniser, env, debug))

    app.add_edge(START, "get_chat_docs")
    app.add_edge("get_chat_docs", "set_chat_prompt_args")
    app.add_edge("set_chat_prompt_args", "set_chat_method")
    app.add_conditional_edges("set_chat_method", lambda state: state["route_name"], {
        ChatRoute.chat: "no_docs_available",
        ChatRoute.chat_with_docs: "llm",
        ChatRoute.chat_with_docs_map_reduce: ChatRoute.chat_with_docs_map_reduce
    })
    app.add_edge(ChatRoute.chat_with_docs_map_reduce, "set_chat_prompt_args")
    return app.compile(debug=debug)

 
def get_chat_with_docs_map_reduce_graph(
    llm: BaseChatModel,
    tokeniser: Encoding,
    env: Settings,
    debug: bool = False
) -> CompiledGraph:   
    
    app = StateGraph(ChatMapReduceState)

    app.add_node("llm_map", build_llm_map_chain(llm, tokeniser, env, env.ai.map_system_prompt, env.ai.chat_map_question_prompt))
    app.add_node("reduce", build_reduce_docs_step(
        TokenTextSplitter(model_name="gpt-4", chunk_size=env.worker_ingest_largest_chunk_size, chunk_overlap=env.worker_ingest_largest_chunk_overlap)
    ))

    app.add_conditional_edges(START, to_map_step, then="reduce")

    return app.compile(debug=debug)