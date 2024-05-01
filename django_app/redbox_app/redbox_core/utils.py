import os


def build_rag_url() -> str:
    return os.environ.get("CORE_API_HOST") + ":" + os.environ.get("CORE_API_PORT") + "/chat/rag"
