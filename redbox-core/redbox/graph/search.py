
from langgraph.graph import StateGraph, START
from langgraph.constants import Send
from langgraph.graph.graph import CompiledGraph
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_text_splitters import TextSplitter, TokenTextSplitter
from tiktoken import Encoding

from redbox.chains.graph import *
from redbox.models.settings import Settings


def get_search_graph(
    llm: BaseChatModel,
    retriever: VectorStoreRetriever,
    tokeniser: Encoding,
    env: Settings,
    debug: bool = False
) -> CompiledGraph:

    app = StateGraph(ChainState)

    app.add_node("get_docs", build_get_docs(env, retriever))
    app.add_node("set_prompt_args", set_prompt_args)

    app.add_node("llm", build_llm_chain(llm, tokeniser, env, env.ai.retrieval_system_prompt, env.ai.retrieval_question_prompt))

    app.add_edge(START, "get_docs")
    app.add_edge("get_docs", "set_prompt_args")
    app.add_edge("set_prompt_args", "llm")

    return app.compile(debug=debug)