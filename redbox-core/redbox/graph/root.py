
from langgraph.graph import StateGraph, START, END
from langchain_core.language_models.chat_models import BaseChatModel
from tiktoken import Encoding

from redbox.chains.graph import *
from redbox.models.chain import ChainInput, ChainState
from redbox.models.settings import Settings
from redbox.chains.components import (
    get_all_chunks_retriever,
    get_chat_llm,
    get_tokeniser
)
from redbox.graph.chat import get_chat_graph, get_chat_with_docs_graph

def get_redbox_graph(
    llm: BaseChatModel,
    all_chunks_retriever: VectorStoreRetriever,
    tokeniser: Encoding,
    env: Settings
):

    app = StateGraph(ChainState)
    app.set_entry_point("set_route")

    app.add_node("set_route", set_route)
    app.add_conditional_edges("set_route", lambda s: s.route_name)

    app.add_node(ChatRoute.chat, set_chat_prompt_args)
    app.add_edge(ChatRoute.chat, "llm_chat")

    app.add_node("llm_chat", build_chat_chain(llm, tokeniser, env))
    app.add_edge("llm_chat", END)

    app.add_node(ChatRoute.chat_with_docs, build_get_chat_docs(env, all_chunks_retriever))
    app.add_edge(ChatRoute.chat_with_docs, "set_chat_prompt_args")

    app.add_node("set_chat_prompt_args", set_chat_prompt_args)
    app.add_conditional_edges("set_chat_prompt_args", chat_method_decision, {
        ChatRoute.chat: "no_docs_available",
        ChatRoute.chat_with_docs: "chat_with_docs_standard",
        ChatRoute.chat_with_docs_map_reduce: "chat_with_docs_map_reduce"
    })

    app.add_node("no_docs_available", no_docs_available)
    app.add_node("chat_with_docs_standard", build_chat_with_docs_chain(llm, tokeniser, env))
    app.add_node("chat_with_docs_map_reduce", build_chat_with_docs_map_reduce_chain())

    return app.compile()


if __name__ == "__main__":
    import os
    logging.basicConfig(stream=sys.stdout, level=os.environ.get("LOG_LEVEL", "INFO"))
    env = Settings()
    all_chunks_retriever = get_all_chunks_retriever(env)
    llm = get_chat_llm(env)
    tokeniser = get_tokeniser()
    app = get_redbox_graph(llm, all_chunks_retriever, tokeniser, env)
    r = app.invoke(
        ChainState(
            query=ChainInput(
                question="What are Labour's five missions?",
                #file_uuids=[],
                file_uuids=["68e5d196-636e-4847-95ad-6c40ba20e390"],
                user_uuid="a93a8f40-f261-4f12-869a-2cea3f3f0d71",
                chat_history=[]
            )
        ),
        debug=True
    )
    state = ChainState.parse_obj(r)
    print(state.route_name)
    print(state.response)
