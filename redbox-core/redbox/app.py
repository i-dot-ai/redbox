from logging import getLogger

from langchain.chat_models import init_chat_model
from langchain_core.messages import BaseMessage
from langchain_core.prompts import PromptTemplate

from redbox.models.chain import RedboxState
from redbox.models.settings import get_settings


async def _default_callback(*args, **kwargs):
    return None


logger = getLogger(__name__)


class Redbox:
    def __init__(self, debug: bool = False):
        self.debug = debug

    def _get_runnable(self, state: RedboxState):
        if state.chat_backend.provider == "google_vertexai":
            return init_chat_model(
                model=state.chat_backend.name,
                model_provider=state.chat_backend.provider,
                location="europe-west1",
                # europe-west1 = Belgium
            )
        return init_chat_model(
            model=state.chat_backend.name,
            model_provider=state.chat_backend.provider,
        )

    def get_messages(self, state: RedboxState) -> list[BaseMessage]:
        settings = get_settings()

        input_state = state.model_dump()
        system_messages = (
            PromptTemplate.from_template(settings.system_prompt_template, template_format="jinja2")
            .invoke(input=input_state)
            .to_messages()
        )
        return system_messages + state.messages

    def run_sync(self, state: RedboxState):
        """
        Run Redbox without streaming events. This simpler, synchronous execution enables use of the graph debug logging
        """
        return self._get_runnable(state).invoke(input=self.get_messages(state))

    async def run(
        self,
        state: RedboxState,
        response_tokens_callback=_default_callback,
    ) -> RedboxState:
        final_state = None
        async for event in self._get_runnable(state).astream_events(
            self.get_messages(state),
            version="v2",
        ):
            kind = event["event"]
            if kind == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                await response_tokens_callback(content)
            elif kind == "on_chain_end":
                final_state = event["data"]["output"]
        return final_state
