from langgraph.graph import END, StateGraph, START
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.vectorstores import VectorStoreRetriever
from tiktoken import Encoding

from redbox.graph.edges import build_conditional_documents_bigger_than_context, make_document_chunk_send
from redbox.graph.nodes import PromptSet, build_merge_pattern, clear_documents, empty_node, set_route, set_state_field
from redbox.models.chain import RedboxQuery, RedboxState
from redbox.models.chat import ChatRoute
from redbox.models.settings import Settings
from redbox.graph.nodes import (
    build_get_docs_with_filter,
    build_llm_chain,
    build_get_docs,
    set_chat_method
)

FINAL_RESPONSE_TAG = "response_flag"
SOURCE_DOCUMENTS_TAG = "source_documents_flag"
ROUTE_NAME_TAG = "route_flag"


# Non keywords
ROUTABLE_BUILTIIN = [ChatRoute.chat, ChatRoute.chat_with_docs, ChatRoute.error_no_keyword]

# Keyword routes
ROUTABLE_KEYWORDS = {ChatRoute.search: "Search for an answer to the question in the document"}

def get_root_graph(
        llm: BaseChatModel,
        all_chunks_retriever: VectorStoreRetriever,
        parameterised_retriever: VectorStoreRetriever,
        env: Settings,
        debug: bool = False,
):
    app = StateGraph(RedboxState)

    app.set_entry_point("set_route")
    app.add_node("set_route", set_route.with_config(tags=[ROUTE_NAME_TAG]))
    app.add_node(ChatRoute.error_no_keyword, set_state_field("text", env.response_no_such_keyword).with_config(tags=[FINAL_RESPONSE_TAG])),

    app.add_conditional_edges(
        "set_route",
        lambda s: s["route_name"],
        {x: x for x in ROUTABLE_BUILTIIN + list(ROUTABLE_KEYWORDS.keys())},
    )
    app.add_edge(ChatRoute.error_no_keyword, END)

    # Search
    app.add_node(ChatRoute.search, empty_node)
    app.add_node("condense_question", build_llm_chain(llm, PromptSet.CondenseQuestion))
    app.add_node("get_docs", build_get_docs_with_filter(parameterised_retriever))
    app.add_node("search_llm", build_llm_chain(llm, PromptSet.Search, final_response_chain=True))

    app.add_edge(ChatRoute.search, "condense_question")
    app.add_edge("condense_question", "get_docs")
    app.add_edge("get_docs", "search_llm")
    app.add_edge("search_llm", END)

    # Chat
    app.add_node(ChatRoute.chat, build_llm_chain(llm, PromptSet.Chat, final_response_chain=True))
    app.add_edge(ChatRoute.chat, END)

    # Chat with Docs
    app.add_node(ChatRoute.chat_with_docs, empty_node)
    app.add_node("get_chat_docs", build_get_docs(all_chunks_retriever))
    app.add_node("documents_larger_than_context_window", empty_node)
    app.add_node("send_chunk_to_shrink", empty_node)
    app.add_node("map_document_to_shorter_answer", build_merge_pattern(llm, PromptSet.ChatwithDocsMapReduce))

    app.add_node("chat_with_docs_llm", build_llm_chain(llm, PromptSet.ChatwithDocs, final_response_chain=True))
    app.add_node("clear_documents", clear_documents)

    app.add_edge(ChatRoute.chat_with_docs, "get_chat_docs")
    app.add_edge("get_chat_docs", "documents_larger_than_context_window")
    app.add_conditional_edges(
        "documents_larger_than_context_window", 
        build_conditional_documents_bigger_than_context(PromptSet.ChatwithDocs), 
        {True: "send_chunk_to_shrink", False: "chat_with_docs_llm"}
    )
    app.add_conditional_edges(
        "send_chunk_to_shrink", 
        make_document_chunk_send("map_document_to_shorter_answer"),
        {"map_document_to_shorter_answer":"map_document_to_shorter_answer"},
        then="chat_with_docs_llm"
    )
    app.add_edge("chat_with_docs_llm", "clear_documents")
    app.add_edge("clear_documents", END)

    return app.compile(debug=debug)


