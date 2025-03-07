import os
from logging import getLogger

from dotenv import load_dotenv
from langchain_core.messages import AIMessage
from langchain_core.prompts import PromptTemplate

from redbox.models.chain import RedboxState
from redbox.models.settings import get_settings
from litellm import acompletion, completion


async def _default_callback(*args, **kwargs):
    return None


logger = getLogger(__name__)
load_dotenv()


def build_messages(state: RedboxState):
    settings = get_settings()
    input_state = state.model_dump()

    system_messages = (
        PromptTemplate.from_template(settings.system_prompt_template, template_format="jinja2")
        .invoke(input=input_state)
        .to_messages()
    )

    return [m.model_dump() for m in  state.messages + system_messages]


class Redbox:
    def __init__(self, debug: bool = False):
        self.debug = debug

    def run_sync(self, state: RedboxState):
        """
        Run Redbox without streaming events. This simpler, synchronous execution enables use of the graph debug logging
        """
        return completion(
            model=f"{state.chat_backend.provider}/{state.chat_backend.name}", messages=build_messages(state)
        )

    async def run(
        self,
        state: RedboxState,
        response_tokens_callback=_default_callback,
    ) -> AIMessage:
        request_dict = state.model_dump()
        logger.info("Request: %s", {k: request_dict[k] for k in request_dict.keys() - {"ai_settings"}})

        if state.chat_backend.provider == "azure_openai":
            provider = "azure"
            kwargs = {"api_base": os.environ["AZURE_OPENAI_ENDPOINT"]}
        elif state.chat_backend.provider == "google_vertexai":
            provider = "vertex_ai"
            kwargs = {"vertex_credentials": os.environ["GOOGLE_APPLICATION_CREDENTIALS_JSON"]}
        elif state.chat_backend.provider == "bedrock":
            provider = "bedrock"
            kwargs = {"modify_params": True}
        else:
            raise ValueError("unrecognized provider")

        response = await acompletion(
            model=f"{provider}/{state.chat_backend.name}", messages=build_messages(state), stream=True, **kwargs
        )
        response_message = []
        async for part in response:
            for choice in part.choices:
                if choice.delta.content:
                    response_message.append(choice.delta.content)
                    await response_tokens_callback(choice.delta.content)

        return AIMessage("".join(response_message))
