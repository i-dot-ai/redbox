
from langchain_openai import AzureChatOpenAI
from langchain_core.utils import convert_to_secret_str
import tiktoken

from redbox.models.settings import Settings
from redbox.retriever.retrievers import AllElasticsearchRetriever


def get_chat_llm(
    env: Settings
):
    return AzureChatOpenAI(
        api_key=convert_to_secret_str(env.azure_openai_api_key),
        azure_endpoint=env.azure_openai_endpoint,
        model=env.azure_openai_model
    )


def get_tokeniser() -> tiktoken.Encoding:
    return tiktoken.get_encoding("cl100k_base")


def get_all_chunks_retriever(
    env: Settings
):
    return AllElasticsearchRetriever(
        es_client=env.elasticsearch_client(),
        index_name=f"{env.elastic_root_index}-chunk",
    )