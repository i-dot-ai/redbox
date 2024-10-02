from enum import StrEnum


class ChatRoute(StrEnum):
    search = "search"
    search_agentic = "gadget"
    chat = "chat"
    chat_with_docs = "chat/documents"
    chat_with_docs_map_reduce = "chat/documents/large"


class ErrorRoute(StrEnum):
    files_too_large = "error/files_too_large"
