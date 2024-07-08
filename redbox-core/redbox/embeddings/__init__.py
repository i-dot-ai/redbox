
from langchain_core.embeddings import Embeddings

from .langchain import get_azure_embeddings, get_openai_embeddings
from redbox.models.settings import Settings


def get_embeddings(env: Settings) -> Embeddings:
    if env.embedding_backend == "azure":
        return get_azure_embeddings(env)
    elif env.embedding_backend == "openai":
        return get_openai_embeddings(env)
    else:
        raise Exception("No configured embedding model")