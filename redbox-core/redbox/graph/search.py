from langgraph.graph import StateGraph, START
from langgraph.graph.graph import CompiledGraph
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.vectorstores import VectorStoreRetriever
from tiktoken import Encoding

from redbox.chains.graph import build_get_docs_with_filter, build_llm_chain, set_prompt_args
from redbox.models.chain import ChainInput, ChainState
from redbox.models.settings import Settings, AISettings


def get_search_graph(
    llm: BaseChatModel,
    retriever: VectorStoreRetriever,
    tokeniser: Encoding,
    env: Settings,
    ai: AISettings,
    debug: bool = False,
) -> CompiledGraph:
    app = StateGraph(ChainState)

    app.add_node("get_docs", build_get_docs_with_filter(ai, retriever))
    app.add_node("set_prompt_args", set_prompt_args)

    app.add_node("condense", build_llm_chain(llm, tokeniser, env, ai))
    app.add_node(
        "map_condense_to_question",
        lambda s: {
            "query": ChainInput(
                question=s["response"],
                file_uuids=s["query"].file_uuids,
                user_uuid=s["query"].user_uuid,
                chat_history=[],
            )
        },
    )
    app.add_node(
        "llm",
        build_llm_chain(
            llm,
            tokeniser,
            env,
            ai,
            final_response_chain=True,
        ),
    )

    app.add_edge(START, "get_docs")
    app.add_edge("get_docs", "set_prompt_args")
    app.add_edge("set_prompt_args", "condense")
    app.add_edge("condense", "map_condense_to_question")
    app.add_edge("map_condense_to_question", "llm")

    return app.compile(debug=debug)
