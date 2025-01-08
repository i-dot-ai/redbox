import logging

from functools import cache

import tiktoken

from dotenv import load_dotenv
from langchain_core.tools import StructuredTool


from redbox.models.settings import ChatLLMBackend
from langchain.chat_models import init_chat_model


logger = logging.getLogger(__name__)
load_dotenv()


def get_chat_llm(model: ChatLLMBackend, tools: list[StructuredTool] | None = None):
    logger.debug("initialising model=%s model_provider=%s tools=%s", model.name, model.provider, tools)
    chat_model = init_chat_model(
        model=model.name,
        model_provider=model.provider,
        configurable_fields=["base_url"],
    )
    if tools:
        chat_model = chat_model.bind_tools(tools)
    return chat_model


@cache
def get_tokeniser() -> tiktoken.Encoding:
    return tiktoken.get_encoding("cl100k_base")
