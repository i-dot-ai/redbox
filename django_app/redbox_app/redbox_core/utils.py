import os
from yarl import URL


def build_core_api_url() -> URL:
    return URL.build(host=os.environ.get("CORE_API_HOST"), port=int(os.environ.get("CORE_API_PORT")))


def build_rag_url() -> URL:
    return build_core_api_url() / "chat/rag"
