import os
from functools import cache, lru_cache

import boto3
import tiktoken
from elasticsearch import ConnectionError, Elasticsearch
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, AnyMessage, BaseMessage
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from litellm import completion, acompletion


class ElasticCloudSettings(BaseModel):
    """settings required for elastic-cloud"""

    model_config = SettingsConfigDict(frozen=True)

    api_key: str
    cloud_id: str
    subscription_level: str = "basic"


class ChatLLMBackend(BaseModel):
    name: str = "gpt-4o"
    provider: str = "azure_openai"
    description: str | None = None
    context_window_size: int = 128_000
    model_config = {"frozen": True}


class Settings(BaseSettings):
    """Settings for the redbox application."""

    elastic: ElasticCloudSettings | None = None
    elastic_chat_message_index: str = "redbox-data-chat-mesage-log"

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

    @lru_cache(1)
    def elasticsearch_client(self) -> Elasticsearch | None:
        if self.elastic is None:
            return None

        client = Elasticsearch(cloud_id=self.elastic.cloud_id, api_key=self.elastic.api_key)

        try:
            if not client.indices.exists(index=self.elastic_chat_message_index):
                client.indices.create(index=self.elastic_chat_message_index)
        except ConnectionError:
            pass

        return client.options(request_timeout=30, retry_on_timeout=True, max_retries=3)

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

    def get_llm(self) -> tuple[str, dict]:
        if self.provider == "azure_openai":
            provider = f"azure/{self.name}"
            kwargs = {"api_base": os.environ["AZURE_OPENAI_ENDPOINT"]}
            return provider, kwargs
        if self.provider == "google_vertexai":
            provider = f"vertex_ai/{self.name}"
            kwargs = {"vertex_credentials": os.environ["GOOGLE_APPLICATION_CREDENTIALS_JSON"]}
            return provider, kwargs
        if self.provider == "bedrock":
            provider = f"bedrock/{self.name}"
            kwargs = {"modify_params": True}
            return provider, kwargs
        raise ValueError("unrecognized provider")

    def get_messages(self) -> list[dict]:
        settings = Settings()

        input_state = self.model_dump()
        system_messages = (
            PromptTemplate.from_template(settings.system_prompt_template, template_format="jinja2")
            .invoke(input=input_state)
            .to_messages()
        )
        return [msg.model_dump() for msg in self.messages + system_messages]


async def _default_callback(*args, **kwargs):
    return None


def run_sync(state: RedboxState) -> BaseMessage:
    """
    Run Redbox without streaming events. This simpler, synchronous execution enables use of the graph debug logging
    """
    model, kwargs = state.get_llm()
    messages = state.get_messages()
    response = completion(model=model, messages=messages, stream=False, **kwargs)
    return response.choices[-1].message


async def run_async(
    state: RedboxState,
    response_tokens_callback=_default_callback,
) -> AIMessage:
    model, kwargs = state.get_llm()
    messages = state.get_messages()
    final_message = ""
    response = await acompletion(model=model, messages=messages, stream=True, **kwargs)
    async for event in response:
        for choice in event.choices:
            if choice.delta.content:
                final_message += choice.delta.content
                await response_tokens_callback(choice.delta.content)
    return AIMessage(content=final_message)
