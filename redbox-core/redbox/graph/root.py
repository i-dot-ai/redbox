
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

    app.add_node(ChatRoute.chat, get_chat_graph(llm, all_chunks_retriever, tokeniser, env))

    app.add_node(ChatRoute.chat_with_docs, get_chat_with_docs_graph(llm, all_chunks_retriever, tokeniser, env))

    app.add_conditional_edges(START, chat_include_docs_decision)

    return app.compile()


if __name__ == "__main__":
    env = Settings()
    all_chunks_retriever = get_all_chunks_retriever(env)
    llm = get_chat_llm(env)
    tokeniser = get_tokeniser()
    app = get_redbox_graph(llm, all_chunks_retriever, tokeniser, env)
    state = app.invoke(
        ChainState(
            query=ChainInput(
                question="What are Labour's five missions?",
                file_uuids=[],
                #file_uuids=["ba43722e-4af5-47ad-8ebb-36be50d609f0"],
                user_uuid="a93a8f40-f261-4f12-869a-2cea3f3f0d71",
                chat_history=[]
            )
        )
    )
    print(state.route_name)
    print(state.response)
