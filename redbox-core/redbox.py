import tiktoken
import logging
import os
from logging import getLogger
from functools import cache, lru_cache


from langchain_core.messages import AIMessage
from langchain.chat_models import init_chat_model
from langchain_core.documents import Document
from langchain_core.messages import AnyMessage, BaseMessage
from langchain_core.prompts import PromptTemplate
from pydantic import Field


import boto3
from elasticsearch import Elasticsearch, ConnectionError
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
from langchain.globals import set_debug

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger()


class ElasticLocalSettings(BaseModel):
    """settings required for a local/ec2 instance of elastic"""

    model_config = SettingsConfigDict(frozen=True)

    host: str = "elasticsearch"
    port: int = 9200
    scheme: str = "http"
    user: str = "elastic"
    version: str = "8.11.0"
    password: str = "redboxpass"
    subscription_level: str = "basic"


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

    elastic: ElasticCloudSettings | ElasticLocalSettings | None = None
    elastic_root_index: str = "redbox-data"

    minio_host: str = "minio"
    minio_port: int = 9000
    aws_access_key: str | None = None
    aws_secret_key: str | None = None

    aws_region: str = "eu-west-2"
    bucket_name: str = "redbox-storage-dev"

    object_store: str = "minio"

    dev_mode: bool = False
    superuser_email: str | None = None

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

    @property
    def elastic_chat_mesage_index(self):
        return self.elastic_root_index + "-chat-mesage-log"

    @lru_cache(1)
    def elasticsearch_client(self) -> Elasticsearch:
        if self.elastic is None:
            return None

        if isinstance(self.elastic, ElasticLocalSettings):
            client = Elasticsearch(
                hosts=[
                    {
                        "host": self.elastic.host,
                        "port": self.elastic.port,
                        "scheme": self.elastic.scheme,
                    }
                ],
                basic_auth=(self.elastic.user, self.elastic.password),
            )

        else:
            client = Elasticsearch(cloud_id=self.elastic.cloud_id, api_key=self.elastic.api_key)

        try:
            if not client.indices.exists(index=self.elastic_chat_mesage_index):
                client.indices.create(index=self.elastic_chat_mesage_index)
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
def get_settings() -> Settings:
    s = Settings()
    set_debug(s.dev_mode)
    return s


@cache
def get_tokeniser() -> tiktoken.Encoding:
    return tiktoken.get_encoding("cl100k_base")


class RedboxState(BaseModel):
    documents: list[Document] = Field(description="List of files to process", default_factory=list)
    messages: list[AnyMessage] = Field(description="All previous messages in chat", default_factory=list)
    chat_backend: ChatLLMBackend = Field(description="User request AI settings", default_factory=ChatLLMBackend)

    def get_llm(self):
        if self.chat_backend.provider == "google_vertexai":
            return init_chat_model(
                model=self.chat_backend.name,
                model_provider=self.chat_backend.provider,
                location="europe-west1",
                # europe-west1 = Belgium
            )
        return init_chat_model(
            model=self.chat_backend.name,
            model_provider=self.chat_backend.provider,
        )

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


logger = getLogger(__name__)


class Redbox:
    def run_sync(self, state: RedboxState):
        """
        Run Redbox without streaming events. This simpler, synchronous execution enables use of the graph debug logging
        """
        return state.get_llm().invoke(input=state.get_messages())

    async def run(
        self,
        state: RedboxState,
        response_tokens_callback=_default_callback,
    ) -> AIMessage:
        final_message = ""
        async for event in state.get_llm().astream_events(
            state.get_messages(),
            version="v2",
        ):
            kind = event["event"]
            if kind == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                final_message += content
                await response_tokens_callback(content)
        return AIMessage(content=final_message)
