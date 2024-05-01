from yarl import URL

from django.conf import settings


def build_core_api_url() -> URL:
    return URL.build(host=settings.CORE_API_HOST, port=int(settings.CORE_API_PORT))


def build_rag_url() -> URL:
    return build_core_api_url() / "chat/rag"
