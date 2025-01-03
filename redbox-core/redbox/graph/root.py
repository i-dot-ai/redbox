from langchain_core.vectorstores import VectorStoreRetriever
from langgraph.graph import END, START, StateGraph
from langgraph.graph.graph import CompiledGraph

from redbox.graph.edges import (
    build_documents_bigger_than_context_conditional,
    build_total_tokens_request_handler_conditional,
    documents_selected_conditional,
    multiple_docs_in_group_conditional,
)
from redbox.graph.nodes.processes import (
    PromptSet,
    build_chat_pattern,
    build_error_pattern,
    build_merge_pattern,
    build_passthrough_pattern,
    build_retrieve_pattern,
    build_set_metadata_pattern,
    build_set_route_pattern,
    build_stuff_pattern,
    clear_documents_process,
    empty_process,
)
from redbox.graph.nodes.sends import build_document_chunk_send, build_document_group_send
from redbox.models.chain import RedboxState
from redbox.models.chat import ChatRoute, ErrorRoute
from redbox.transform import structure_documents_by_file_name


def get_chat_graph(
    debug: bool = False,
) -> CompiledGraph:
    """Creates a subgraph for standard chat."""
    builder = StateGraph(RedboxState)

    # Processes
    builder.add_node("p_set_chat_route", build_set_route_pattern(route=ChatRoute.chat))
    builder.add_node(
        "p_chat",
        build_chat_pattern(prompt_set=PromptSet.Chat, final_response_chain=True),
    )

    # Edges
    builder.add_edge(START, "p_set_chat_route")
    builder.add_edge("p_set_chat_route", "p_chat")
    builder.add_edge("p_chat", END)

    return builder.compile(debug=debug)


def get_chat_with_documents_large_graph():
    """a subgraph for get_chat_with_documents_graph"""
    builder = StateGraph(RedboxState)

    # Sends
    builder.add_node("s_chunk", empty_process)
    builder.add_node("s_group_1", empty_process)
    builder.add_node("s_group_2", empty_process)
    builder.add_node("p_too_large_error", empty_process)

    builder.add_node(
        "p_summarise_each_document",
        build_merge_pattern(prompt_set=PromptSet.ChatwithDocsMapReduce),
    )
    builder.add_node(
        "p_summarise_document_by_document",
        build_merge_pattern(prompt_set=PromptSet.ChatwithDocsMapReduce),
    )
    builder.add_node(
        "p_summarise",
        build_stuff_pattern(
            prompt_set=PromptSet.ChatwithDocs,
            final_response_chain=True,
        ),
    )
    builder.add_node("p_clear_documents", clear_documents_process)

    builder.add_node("d_groups_have_multiple_docs", empty_process)
    builder.add_node("d_doc_summaries_bigger_than_context", empty_process)
    builder.add_node("d_single_doc_summaries_bigger_than_context", empty_process)

    # Edges
    builder.add_edge(START, "s_chunk")
    builder.add_conditional_edges(
        "s_chunk",
        build_document_chunk_send("p_summarise_each_document"),
        path_map=["p_summarise_each_document"],
    )
    builder.add_edge("p_summarise_each_document", "d_groups_have_multiple_docs")

    builder.add_conditional_edges(
        "d_groups_have_multiple_docs",
        multiple_docs_in_group_conditional,
        {
            True: "s_group_1",
            False: "d_doc_summaries_bigger_than_context",
        },
    )

    builder.add_conditional_edges(
        "s_group_1",
        build_document_group_send("d_single_doc_summaries_bigger_than_context"),
        path_map=["d_single_doc_summaries_bigger_than_context"],
    )
    builder.add_conditional_edges(
        "d_single_doc_summaries_bigger_than_context",
        build_documents_bigger_than_context_conditional(PromptSet.ChatwithDocsMapReduce),
        {
            True: "p_too_large_error",
            False: "s_group_2",
        },
    )
    builder.add_conditional_edges(
        "s_group_2",
        build_document_group_send("p_summarise_document_by_document"),
        path_map=["p_summarise_document_by_document"],
    )
    builder.add_edge("p_summarise_document_by_document", "d_doc_summaries_bigger_than_context")

    builder.add_conditional_edges(
        "d_doc_summaries_bigger_than_context",
        build_documents_bigger_than_context_conditional(PromptSet.ChatwithDocs),
        {
            True: "p_too_large_error",
            False: "p_summarise",
        },
    )
    builder.add_edge("p_summarise", "p_clear_documents")

    builder.add_edge("p_too_large_error", END)
    builder.add_edge("p_clear_documents", END)

    return builder.compile()


def get_chat_with_documents_graph(
    retriever: VectorStoreRetriever,
    debug: bool = False,
) -> CompiledGraph:
    """Creates a subgraph for chatting with documents."""
    builder = StateGraph(RedboxState)

    # Processes
    builder.add_node("p_pass_question_to_text", build_passthrough_pattern())
    builder.add_node("p_set_chat_docs_route", build_set_route_pattern(route=ChatRoute.chat_with_docs))
    builder.add_node(
        "p_set_chat_docs_map_reduce_route",
        build_set_route_pattern(route=ChatRoute.chat_with_docs_map_reduce),
    )
    builder.add_node(
        "p_summarise",
        build_stuff_pattern(
            prompt_set=PromptSet.ChatwithDocs,
            final_response_chain=True,
        ),
    )
    builder.add_node("p_clear_documents", clear_documents_process)
    builder.add_node(
        "p_too_large_error",
        build_error_pattern(
            text="These documents are too large to work with.",
            route_name=ErrorRoute.files_too_large,
        ),
    )
    builder.add_node(
        "p_retrieve_all_chunks",
        build_retrieve_pattern(
            retriever=retriever,
            structure_func=structure_documents_by_file_name,
            final_source_chain=True,
        ),
    )

    builder.add_node("chat_with_documents_large", get_chat_with_documents_large_graph())

    # Decisions
    builder.add_node("d_request_handler_from_total_tokens", empty_process)

    # Edges
    builder.add_edge(START, "p_pass_question_to_text")
    builder.add_edge("p_pass_question_to_text", "d_request_handler_from_total_tokens")
    builder.add_conditional_edges(
        "d_request_handler_from_total_tokens",
        build_total_tokens_request_handler_conditional(PromptSet.ChatwithDocsMapReduce),
        {
            "max_exceeded": "p_too_large_error",
            "context_exceeded": "p_set_chat_docs_map_reduce_route",
            "pass": "p_set_chat_docs_route",
        },
    )
    builder.add_edge("p_set_chat_docs_route", "p_retrieve_all_chunks")
    builder.add_edge("p_set_chat_docs_map_reduce_route", "p_retrieve_all_chunks")
    builder.add_conditional_edges(
        "p_retrieve_all_chunks",
        lambda s: s.route_name,
        {
            ChatRoute.chat_with_docs: "p_summarise",
            ChatRoute.chat_with_docs_map_reduce: "chat_with_documents_large",
        },
    )
    builder.add_edge("p_summarise", "p_clear_documents")
    builder.add_edge("p_clear_documents", END)
    builder.add_edge("p_too_large_error", END)
    builder.add_edge("chat_with_documents_large", END)

    return builder.compile(debug=debug)


def get_retrieve_metadata_graph(retriever: VectorStoreRetriever, debug: bool = False):
    builder = StateGraph(RedboxState)

    # Processes
    builder.add_node(
        "p_retrieve_metadata",
        build_retrieve_pattern(
            retriever=retriever,
            structure_func=structure_documents_by_file_name,
        ),
    )
    builder.add_node("p_set_metadata", build_set_metadata_pattern())
    builder.add_node("p_clear_metadata_documents", clear_documents_process)

    # Edges
    builder.add_edge(START, "p_retrieve_metadata")
    builder.add_edge("p_retrieve_metadata", "p_set_metadata")
    builder.add_edge("p_set_metadata", "p_clear_metadata_documents")
    builder.add_edge("p_clear_metadata_documents", END)

    return builder.compile(debug=debug)


# Root graph
def get_root_graph(
    retriever: VectorStoreRetriever,
    debug: bool = False,
) -> CompiledGraph:
    """Creates the core Redbox graph."""
    builder = StateGraph(RedboxState)

    # Subgraphs
    chat_subgraph = get_chat_graph(debug=debug)
    cwd_subgraph = get_chat_with_documents_graph(
        retriever=retriever,
        debug=debug,
    )
    metadata_subgraph = get_retrieve_metadata_graph(retriever=retriever, debug=debug)

    # Processes
    builder.add_node("p_chat", chat_subgraph)
    builder.add_node("p_chat_with_documents", cwd_subgraph)
    builder.add_node("p_retrieve_metadata", metadata_subgraph)

    # Log

    # Decisions
    builder.add_node("d_docs_selected", empty_process)

    # Edges
    builder.add_edge(START, "p_retrieve_metadata")
    builder.add_edge("p_retrieve_metadata", "d_docs_selected")
    builder.add_conditional_edges(
        "d_docs_selected",
        documents_selected_conditional,
        {
            True: "p_chat_with_documents",
            False: "p_chat",
        },
    )
    builder.add_edge("p_chat", END)
    builder.add_edge("p_chat_with_documents", END)

    return builder.compile(debug=debug)
