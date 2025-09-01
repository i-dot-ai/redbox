import os
from functools import cache

import boto3
import datetime
import tiktoken
from _datetime import timedelta
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, AnyMessage, BaseMessage
from langchain_core.prompts import PromptTemplate
from langchain_openai import OpenAI, ChatOpenAI
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

import litellm
import os


class ChatLLMBackend(BaseModel):
    name: str = "gpt-4o"
    provider: str = "azure_openai"
    description: str | None = None
    context_window_size: int = 128_000
    model_config = {"frozen": True}


class Settings(BaseSettings):
    """Settings for the redbox application."""

    minio_host: str = "minio"
    minio_port: int = 9000
    aws_access_key: str | None = None
    aws_secret_key: str | None = None

    aws_region: str = "eu-west-2"
    bucket_name: str = "redbox-storage-dev"

    object_store: str = "minio"

    system_prompt_template: str = """You are Redbox, an AI assistant to civil servants in the United Kingdom.

You follow instructions and respond to queries accurately and concisely, and are professional in all your
interactions with users. You use British English spellings and phrases rather than American English.

{% if documents is defined and documents|length > 0 %}
Use the following documents as primary sources for information and use them to respond to the users queries

{% for d in documents %}
Title: {{d.metadata.get("uri", "unknown document")}}
{{d.page_content}}

{% endfor %}
{% endif %}
"""

    model_config = SettingsConfigDict(env_file=".env", env_nested_delimiter="__", extra="allow", frozen=True)

    def s3_client(self):
        if self.object_store == "minio":
            return boto3.client(
                "s3",
                aws_access_key_id=self.aws_access_key or "",
                aws_secret_access_key=self.aws_secret_key or "",
                endpoint_url=f"http://{self.minio_host}:{self.minio_port}",
            )

        if self.object_store == "s3":
            return boto3.client(
                "s3",
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_key,
                region_name=self.aws_region,
            )

        msg = f"unknown object_store={self.object_store}"
        raise NotImplementedError(msg)


@cache
def get_tokeniser() -> tiktoken.Encoding:
    return tiktoken.get_encoding("cl100k_base")


class RedboxState(BaseModel):
    documents: list[Document] = Field(description="List of files to process", default_factory=list)
    messages: list[AnyMessage] = Field(description="All previous messages in chat", default_factory=list)
    chat_backend: ChatLLMBackend = Field(description="User request AI settings", default_factory=ChatLLMBackend)

    def get_model_name(self):
        match self.chat_backend.name:
            case "anthropic.claude-3-sonnet-20240229-v1:0":
                return "bedrock-claude-3-sonnet"
            case "anthropic.claude-3-haiku-20240307-v1:0":
                return "bedrock-claude-3-haiku"
            case "gemini-2.0-flash-001":
                return "gemini-2-flash"
            case _:
                return self.chat_backend.name

    def get_llm(self):
        api_key = os.environ["LITELLM_PROXY_API_KEY"]
        base_url = os.environ["LITELLM_PROXY_API_BASE"]
        model = self.get_model_name()
        return ChatOpenAI(model=model, base_url=base_url, api_key=api_key)

    def get_messages(self) -> list[BaseMessage]:
        settings = Settings()

        input_state = self.model_dump()
        system_messages = (
            PromptTemplate.from_template(settings.system_prompt_template, template_format="jinja2")
            .invoke(input=input_state)
            .to_messages()
        )
        return system_messages + self.messages


async def _default_callback(*args, **kwargs):
    return None


def run_sync(state: RedboxState) -> tuple[BaseMessage, timedelta]:
    """
    Run Redbox without streaming events. This simpler, synchronous execution enables use of the graph debug logging
    """
    start = datetime.datetime.now()
    result = state.get_llm().invoke(input=state.get_messages())
    end = datetime.datetime.now()
    return result, end - start


async def run_async(
    state: RedboxState,
    response_tokens_callback=_default_callback,
) -> tuple[AIMessage, timedelta]:
    start = datetime.datetime.now()
    final_message = ""
    async for chunk in state.get_llm().astream(
        state.get_messages(),
    ):
        final_message += chunk.content
        await response_tokens_callback(chunk.content)
    return AIMessage(content=final_message), datetime.datetime.now() - start
