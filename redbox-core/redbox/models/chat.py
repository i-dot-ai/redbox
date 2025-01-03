from enum import StrEnum


class ChatRoute(StrEnum):
    chat = "chat"
    chat_with_docs = "chat/documents"


class ErrorRoute(StrEnum):
    files_too_large = "error/files_too_large"
