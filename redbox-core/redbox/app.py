from logging import getLogger

from langchain_core.messages import AIMessage

from redbox.models.chain import RedboxState


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
        final_state = None
        async for event in state.get_llm().astream_events(
            state.get_messages(),
            version="v2",
        ):
            kind = event["event"]
            if kind == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                await response_tokens_callback(content)
            elif kind == "on_chain_end":
                final_state = event["data"]["output"]
        return final_state
