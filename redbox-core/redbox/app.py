from logging import getLogger

from redbox.chains.components import get_chat_llm
from redbox.chains.runnables import build_llm_chain
from redbox.models.chain import RedboxState


async def _default_callback(*args, **kwargs):
    return None


logger = getLogger(__name__)


class Redbox:
    def __init__(self, debug: bool = False):
        self.debug = debug

    def _get_runnable(self, state: RedboxState):
        return build_llm_chain(llm=get_chat_llm(state.request.ai_settings.chat_backend))

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
        request_dict = input.request.model_dump()
        logger.info("Request: %s", {k: request_dict[k] for k in request_dict.keys() - {"ai_settings"}})
        async for event in self._get_runnable(input).astream_events(
            input,
            version="v2",
            config={"recursion_limit": input.request.ai_settings.recursion_limit},
        ):
            kind = event["event"]
            if kind == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                await response_tokens_callback(content)
            elif kind == "on_chain_end":
                final_state = event["data"]["output"]
        return final_state
