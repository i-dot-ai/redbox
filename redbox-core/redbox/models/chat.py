from enum import StrEnum


class ChatRoute(StrEnum):
    search = "search"
    gadget = "search/agentic"
    chat = "chat"
    chat_with_docs = "chat/documents"
    chat_with_docs_map_reduce = "chat/documents/large"
    react = "react"


class ErrorRoute(StrEnum):
    files_too_large = "error/files_too_large"
