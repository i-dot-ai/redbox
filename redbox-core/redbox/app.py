from logging import getLogger

from langchain.chat_models import init_chat_model

from redbox.chains.runnables import build_chat_prompt_from_messages_runnable
from redbox.models.chain import RedboxState


async def _default_callback(*args, **kwargs):
    return None


logger = getLogger(__name__)


class Redbox:
    def __init__(self, debug: bool = False):
        self.debug = debug

    def _get_runnable(self, state: RedboxState):
        llm = init_chat_model(
            model=state.ai_settings.chat_backend.name,
            model_provider=state.ai_settings.chat_backend.provider,
            configurable_fields=["base_url"],
        )

        return build_chat_prompt_from_messages_runnable() | llm

    def run_sync(self, input: RedboxState):
        """
        Run Redbox without streaming events. This simpler, synchronous execution enables use of the graph debug logging
        """
        return self._get_runnable(input).invoke(input=input)

    async def run(
        self,
        input: RedboxState,
        response_tokens_callback=_default_callback,
    ) -> RedboxState:
        final_state = None
        request_dict = input.model_dump()
        logger.info("Request: %s", {k: request_dict[k] for k in request_dict.keys() - {"ai_settings"}})
        async for event in self._get_runnable(input).astream_events(
            input,
            version="v2",
        ):
            kind = event["event"]
            if kind == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                await response_tokens_callback(content)
            elif kind == "on_chain_end":
                final_state = event["data"]["output"]
        return final_state
