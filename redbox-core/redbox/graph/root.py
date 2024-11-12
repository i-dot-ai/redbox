from langchain_core.tools import StructuredTool
from langchain_core.vectorstores import VectorStoreRetriever
from langgraph.graph import END, START, StateGraph
from langgraph.graph.graph import CompiledGraph

from redbox.chains.components import get_structured_response_with_citations_parser
from redbox.chains.runnables import build_self_route_output_parser
from redbox.graph.edges import (
    build_documents_bigger_than_context_conditional,
    build_keyword_detection_conditional,
    build_tools_selected_conditional,
    build_total_tokens_request_handler_conditional,
    documents_selected_conditional,
    multiple_docs_in_group_conditional,
)
from redbox.graph.nodes.processes import (
    PromptSet,
    build_activity_log_node,
    build_chat_pattern,
    build_error_pattern,
    build_merge_pattern,
    build_passthrough_pattern,
    build_retrieve_pattern,
    build_set_metadata_pattern,
    build_set_route_pattern,
    build_set_self_route_from_llm_answer,
    build_stuff_pattern,
    build_tool_pattern,
    clear_documents_process,
    empty_process,
    report_sources_process,
)
from redbox.graph.nodes.sends import build_document_chunk_send, build_document_group_send, build_tool_send
from redbox.graph.nodes.tools import get_log_formatter_for_retrieval_tool
from redbox.models.chain import RedboxState
from redbox.models.chat import ChatRoute, ErrorRoute
from redbox.models.graph import ROUTABLE_KEYWORDS, RedboxActivityEvent
from redbox.transform import structure_documents_by_file_name, structure_documents_by_group_and_indices


def get_self_route_graph(retriever: VectorStoreRetriever, prompt_set: PromptSet, debug: bool = False):
    builder = StateGraph(RedboxState)

    def self_route_question_is_unanswerable(llm_response: str):
        return "unanswerable" in llm_response

    # Processes
    builder.add_node("p_condense_question", build_chat_pattern(prompt_set=PromptSet.CondenseQuestion))
    builder.add_node(
        "p_retrieve_docs",
        build_retrieve_pattern(
            retriever=retriever,
            structure_func=structure_documents_by_file_name,
            final_source_chain=False,
        ),
    )
    builder.add_node(
        "p_answer_question_or_decide_unanswerable",
        build_stuff_pattern(
            prompt_set=prompt_set,
            output_parser=build_self_route_output_parser(
                match_condition=self_route_question_is_unanswerable,
                max_tokens_to_check=4,
                final_response_chain=True,
            ),
            final_response_chain=False,
        ),
    )
    builder.add_node(
        "p_set_route_name_from_answer",
        build_set_self_route_from_llm_answer(
            self_route_question_is_unanswerable,
            true_condition_state_update={"route_name": ChatRoute.chat_with_docs_map_reduce},
            false_condition_state_update={"route_name": ChatRoute.search},
        ),
    )
    builder.add_node("p_clear_documents", clear_documents_process)

    # Edges
    builder.add_edge(START, "p_condense_question")
    builder.add_edge("p_condense_question", "p_retrieve_docs")
    builder.add_edge("p_retrieve_docs", "p_answer_question_or_decide_unanswerable")
    builder.add_edge("p_answer_question_or_decide_unanswerable", "p_set_route_name_from_answer")
    builder.add_conditional_edges(
        "p_set_route_name_from_answer",
        lambda state: state["route_name"],
        {
            ChatRoute.chat_with_docs_map_reduce: "p_clear_documents",
            ChatRoute.search: END,
        },
    )
    builder.add_edge("p_clear_documents", END)

    return builder.compile(debug=debug)


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


def get_search_graph(
    retriever: VectorStoreRetriever,
    prompt_set: PromptSet = PromptSet.Search,
    debug: bool = False,
    final_sources: bool = True,
    final_response: bool = True,
) -> CompiledGraph:
    """Creates a subgraph for retrieval augmented generation (RAG)."""
    builder = StateGraph(RedboxState)

    # Processes
    builder.add_node("p_set_search_route", build_set_route_pattern(route=ChatRoute.search))
    builder.add_node("p_condense_question", build_chat_pattern(prompt_set=PromptSet.CondenseQuestion))
    builder.add_node(
        "p_retrieve_docs",
        build_retrieve_pattern(
            retriever=retriever,
            structure_func=structure_documents_by_group_and_indices,
            final_source_chain=final_sources,
        ),
    )
    builder.add_node(
        "p_stuff_docs",
        build_stuff_pattern(prompt_set=prompt_set, final_response_chain=final_response),
    )

    # Edges
    builder.add_edge(START, "p_set_search_route")
    builder.add_edge("p_set_search_route", "p_condense_question")
    builder.add_edge("p_condense_question", "p_retrieve_docs")
    builder.add_edge("p_retrieve_docs", "p_stuff_docs")
    builder.add_edge("p_stuff_docs", END)

    return builder.compile(debug=debug)


def get_agentic_search_graph(tools: dict[str, StructuredTool], debug: bool = False) -> CompiledGraph:
    """Creates a subgraph for agentic RAG."""

    citations_output_parser, format_instructions = get_structured_response_with_citations_parser()
    builder = StateGraph(RedboxState)
    # Tools
    agent_tool_names = ["_search_documents", "_search_wikipedia", "_search_govuk"]
    agent_tools: list[StructuredTool] = tuple([tools.get(tool_name) for tool_name in agent_tool_names])

    # Processes
    builder.add_node("p_set_agentic_search_route", build_set_route_pattern(route=ChatRoute.gadget))
    builder.add_node(
        "p_search_agent",
        build_stuff_pattern(
            prompt_set=PromptSet.SearchAgentic,
            tools=agent_tools,
            output_parser=citations_output_parser,
            format_instructions=format_instructions,
            final_response_chain=False,  # Output parser handles streaming
        ),
    )
    builder.add_node(
        "p_retrieval_tools",
        build_tool_pattern(tools=agent_tools, final_source_chain=False),
    )
    builder.add_node(
        "p_give_up_agent",
        build_stuff_pattern(prompt_set=PromptSet.GiveUpAgentic, final_response_chain=True),
    )
    builder.add_node("p_report_sources", report_sources_process)

    # Log
    builder.add_node(
        "p_activity_log_retrieval_tool_calls",
        build_activity_log_node(
            lambda s: [
                RedboxActivityEvent(message=get_log_formatter_for_retrieval_tool(tool_state_entry["tool"]).log_call())
                for tool_state_entry in s["tool_calls"].values()
                if not tool_state_entry["called"]
            ]
        ),
    )

    # Decisions
    builder.add_node("d_x_steps_left_or_less", empty_process)

    # Sends
    builder.add_node("s_tool", empty_process)

    # Edges
    builder.add_edge(START, "p_set_agentic_search_route")
    builder.add_edge("p_set_agentic_search_route", "d_x_steps_left_or_less")
    builder.add_conditional_edges(
        "d_x_steps_left_or_less",
        lambda state: state["steps_left"] <= 8,
        {
            True: "p_give_up_agent",
            False: "p_search_agent",
        },
    )
    builder.add_conditional_edges(
        "p_search_agent",
        build_tools_selected_conditional(tools=agent_tool_names),
        {True: "s_tool", False: "p_report_sources"},
    )
    builder.add_edge("p_search_agent", "p_activity_log_retrieval_tool_calls")
    builder.add_conditional_edges("s_tool", build_tool_send("p_retrieval_tools"), path_map=["p_retrieval_tools"])
    builder.add_edge("p_retrieval_tools", "d_x_steps_left_or_less")
    builder.add_edge("p_report_sources", END)

    return builder.compile(debug=debug)


def get_chat_with_documents_graph(
    all_chunks_retriever: VectorStoreRetriever,
    parameterised_retriever: VectorStoreRetriever,
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
    builder.add_node(
        "p_too_large_error",
        build_error_pattern(
            text="These documents are too large to work with.",
            route_name=ErrorRoute.files_too_large,
        ),
    )
    builder.add_node(
        "p_answer_or_decide_route",
        get_self_route_graph(parameterised_retriever, PromptSet.SelfRoute),
    )
    builder.add_node(
        "p_retrieve_all_chunks",
        build_retrieve_pattern(
            retriever=all_chunks_retriever,
            structure_func=structure_documents_by_file_name,
            final_source_chain=True,
        ),
    )

    builder.add_node(
        "p_activity_log_tool_decision",
        build_activity_log_node(lambda state: RedboxActivityEvent(message=f"Using _{state["route_name"]}_")),
    )

    # Decisions
    builder.add_node("d_request_handler_from_total_tokens", empty_process)
    builder.add_node("d_single_doc_summaries_bigger_than_context", empty_process)
    builder.add_node("d_doc_summaries_bigger_than_context", empty_process)
    builder.add_node("d_groups_have_multiple_docs", empty_process)
    builder.add_node("d_self_route_is_enabled", empty_process)

    # Sends
    builder.add_node("s_chunk", empty_process)
    builder.add_node("s_group_1", empty_process)
    builder.add_node("s_group_2", empty_process)

    # Edges
    builder.add_edge(START, "p_pass_question_to_text")
    builder.add_edge("p_pass_question_to_text", "d_request_handler_from_total_tokens")
    builder.add_conditional_edges(
        "d_request_handler_from_total_tokens",
        build_total_tokens_request_handler_conditional(PromptSet.ChatwithDocsMapReduce),
        {
            "max_exceeded": "p_too_large_error",
            "context_exceeded": "d_self_route_is_enabled",
            "pass": "p_set_chat_docs_route",
        },
    )
    builder.add_conditional_edges(
        "d_self_route_is_enabled",
        lambda s: s["request"].ai_settings.self_route_enabled,
        {True: "p_answer_or_decide_route", False: "p_set_chat_docs_map_reduce_route"},
        then="p_activity_log_tool_decision",
    )
    builder.add_conditional_edges(
        "p_answer_or_decide_route",
        lambda state: state.get("route_name"),
        {
            ChatRoute.search: END,
            ChatRoute.chat_with_docs_map_reduce: "p_retrieve_all_chunks",
        },
    )
    builder.add_edge("p_set_chat_docs_route", "p_retrieve_all_chunks")
    builder.add_edge("p_set_chat_docs_map_reduce_route", "p_retrieve_all_chunks")
    builder.add_conditional_edges(
        "p_retrieve_all_chunks",
        lambda s: s["route_name"],
        {
            ChatRoute.chat_with_docs: "p_summarise",
            ChatRoute.chat_with_docs_map_reduce: "s_chunk",
        },
    )
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
    builder.add_edge("p_clear_documents", END)
    builder.add_edge("p_too_large_error", END)

    return builder.compile(debug=debug)


def get_retrieve_metadata_graph(metadata_retriever: VectorStoreRetriever, debug: bool = False):
    builder = StateGraph(RedboxState)

    # Processes
    builder.add_node(
        "p_retrieve_metadata",
        build_retrieve_pattern(
            retriever=metadata_retriever,
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
    all_chunks_retriever: VectorStoreRetriever,
    parameterised_retriever: VectorStoreRetriever,
    metadata_retriever: VectorStoreRetriever,
    tools: dict[str, StructuredTool],
    debug: bool = False,
) -> CompiledGraph:
    """Creates the core Redbox graph."""
    builder = StateGraph(RedboxState)

    # Subgraphs
    chat_subgraph = get_chat_graph(debug=debug)
    rag_subgraph = get_search_graph(retriever=parameterised_retriever, debug=debug)
    agent_subgraph = get_agentic_search_graph(tools=tools, debug=debug)
    cwd_subgraph = get_chat_with_documents_graph(
        all_chunks_retriever=all_chunks_retriever,
        parameterised_retriever=parameterised_retriever,
        debug=debug,
    )
    metadata_subgraph = get_retrieve_metadata_graph(metadata_retriever=metadata_retriever, debug=debug)

    # Processes
    builder.add_node("p_search", rag_subgraph)
    builder.add_node("p_search_agentic", agent_subgraph)
    builder.add_node("p_chat", chat_subgraph)
    builder.add_node("p_chat_with_documents", cwd_subgraph)
    builder.add_node("p_retrieve_metadata", metadata_subgraph)

    # Log
    builder.add_node(
        "p_activity_log_user_request",
        build_activity_log_node(
            lambda s: [
                RedboxActivityEvent(
                    message=f"You selected {len(s["request"].s3_keys)} file{"s" if len(s["request"].s3_keys)>1 else ""} - {",".join(s["request"].s3_keys)}"
                )
                if len(s["request"].s3_keys) > 0
                else "You selected no files",
            ]
        ),
    )

    # Decisions
    builder.add_node("d_keyword_exists", empty_process)
    builder.add_node("d_docs_selected", empty_process)

    # Edges
    builder.add_edge(START, "p_activity_log_user_request")
    builder.add_edge(START, "p_retrieve_metadata")
    builder.add_edge("p_retrieve_metadata", "d_keyword_exists")
    builder.add_conditional_edges(
        "d_keyword_exists",
        build_keyword_detection_conditional(*ROUTABLE_KEYWORDS.keys()),
        {
            ChatRoute.search: "p_search",
            ChatRoute.gadget: "p_search_agentic",
            "DEFAULT": "d_docs_selected",
        },
    )
    builder.add_conditional_edges(
        "d_docs_selected",
        documents_selected_conditional,
        {
            True: "p_chat_with_documents",
            False: "p_chat",
        },
    )
    builder.add_edge("p_search", END)
    builder.add_edge("p_search_agentic", END)
    builder.add_edge("p_chat", END)
    builder.add_edge("p_chat_with_documents", END)

    return builder.compile(debug=debug)
