from langchain_core.embeddings import Embeddings
from langchain_huggingface import HuggingFaceEmbeddings
from redbox.models.settings import Settings

from .langchain import get_azure_embeddings, get_openai_embeddings


def get_embeddings(env: Settings) -> Embeddings:
    if env.embedding_backend == "azure":
        return get_azure_embeddings(env)
    elif env.embedding_backend == "openai":
        return get_openai_embeddings(env)
    elif env.embedding_backend == "sentencetransformers":
        return HuggingFaceEmbeddings(
            model_name=env.embedding_openai_model,
        )
    else:
        raise Exception("No configured embedding model")
