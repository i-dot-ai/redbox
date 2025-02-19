import os
from logging import getLogger

from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate

from redbox.models.chain import RedboxState
from redbox.models.settings import get_settings


async def _default_callback(*args, **kwargs):
    return None


logger = getLogger(__name__)


class Redbox:
    def __init__(self, debug: bool = False):
        self.debug = debug

    def _get_runnable(self, state: RedboxState):
        azure_endpoint = f"http://{os.environ['LITELLM_URL']}:4000"
        api_key = os.environ["LITELLM_MASTER_KEY"]
        logger.info("LITELLM_URL=%s, LITELLM_MASTER_KEY=%s", azure_endpoint, api_key)
        settings = get_settings()
        if state.chat_backend.provider == "google_vertexai":
            llm = init_chat_model(
                model=state.chat_backend.name,
                model_provider=state.chat_backend.provider,
                location="europe-west1",
                # europe-west1 = Belgium
            )
        else:
            llm = init_chat_model(
            azure_endpoint=azure_endpoint,
            api_key=api_key,
            model=state.chat_backend.name,
            model_provider=state.chat_backend.provider,
            )

        input_state = state.model_dump()
        messages = (
            [settings.system_prompt_template]
            + state.messages[:-1]
            + PromptTemplate.from_template(settings.question_prompt_template, template_format="jinja2")
            .invoke(input=input_state)
            .to_messages()
        )
        return ChatPromptTemplate.from_messages(messages=messages) | llm

    def run_sync(self, state: RedboxState):
        """
        Run Redbox without streaming events. This simpler, synchronous execution enables use of the graph debug logging
        """
        request_dict = state.model_dump()
        return self._get_runnable(state).invoke(input=request_dict)

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
