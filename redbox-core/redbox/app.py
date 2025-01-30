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

Context: previous messages:
{chat_history}

Context: user documents:
{documents}

Question to answer:
{question}

Answer:
"""


class Redbox:
    def __init__(self, debug: bool = False):
        self.debug = debug

    def _get_runnable(self, state: RedboxState):
        llm = init_chat_model(
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
        question, chat_history = request_dict["messages"][-1], request_dict["messages"][:-1]
        request_dict["question"] = question
        request_dict["chat_history"] = chat_history

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
