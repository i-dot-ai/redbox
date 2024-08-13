from langchain_openai.embeddings import AzureOpenAIEmbeddings, OpenAIEmbeddings
from langchain_core.utils.utils import convert_to_secret_str

from redbox.models.settings import Settings


def get_azure_embeddings(env: Settings):
    return AzureOpenAIEmbeddings(
        azure_endpoint=env.azure_openai_endpoint,
        api_version=env.azure_api_version_embeddings,
        model=env.azure_embedding_model,
        max_retries=env.embedding_max_retries,
        retry_min_seconds=env.embedding_retry_min_seconds,
        retry_max_seconds=env.embedding_retry_max_seconds,
    )


def get_openai_embeddings(env: Settings):
    return OpenAIEmbeddings(
        api_key=convert_to_secret_str(env.openai_api_key),
        base_url=env.embedding_openai_base_url,
        model=env.embedding_openai_model,
        chunk_size=env.embedding_max_batch_size,
    )
