import os
from logging import getLogger

from langchain.chat_models import init_chat_model
from langchain_core.prompts import PromptTemplate

from redbox.models.chain import RedboxState


async def _default_callback(*args, **kwargs):
    return None


logger = getLogger(__name__)

prompt_template = """You are Redbox, an AI assistant to civil servants in the United Kingdom.

You follow instructions and respond to queries accurately and concisely, and are professional in all your
interactions with users.

You are tasked with providing information objectively and responding helpfully to users using context from their
provided documents

Messages:
{messages}

Documents:
{documents}

Answer:
"""


class Redbox:
    def __init__(self, debug: bool = False):
        self.debug = debug

    def _get_runnable(self, state: RedboxState):
        azure_endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
        api_key = os.environ["LITELLM_MASTER_KEY"]
        logger.info("AZURE_OPENAI_ENDPOINT=%s, LITELLM_MASTER_KEY=%s", azure_endpoint, api_key)

        llm = init_chat_model(
            azure_endpoint=azure_endpoint,
            api_key=api_key,
            model=state.chat_backend.name,
            model_provider=state.chat_backend.provider,
        )

        return PromptTemplate.from_template(prompt_template) | llm

    def run_sync(self, input: RedboxState):
        """
        Run Redbox without streaming events. This simpler, synchronous execution enables use of the graph debug logging
        """
        return self._get_runnable(input).invoke(input=input)

    async def run(
        self,
        state: RedboxState,
        response_tokens_callback=_default_callback,
    ) -> RedboxState:
        final_state = None
        request_dict = state.model_dump()
        logger.info("Request: %s", {k: request_dict[k] for k in request_dict.keys() - {"ai_settings"}})
        async for event in self._get_runnable(state).astream_events(
            request_dict,
            version="v2",
        ):
            kind = event["event"]
            if kind == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                await response_tokens_callback(content)
            elif kind == "on_chain_end":
                final_state = event["data"]["output"]
        return final_state
