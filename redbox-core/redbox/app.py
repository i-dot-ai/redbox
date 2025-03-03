import pathlib
from logging import getLogger

from langgraph.prebuilt import create_react_agent
from langchain.chat_models import init_chat_model
from langchain_mcp import MCPToolkit
from mcp import stdio_client, ClientSession, StdioServerParameters

from redbox.models.chain import RedboxState
from redbox.models.settings import get_settings


async def _default_callback(*args, **kwargs):
    return None


logger = getLogger(__name__)


class Redbox:
    def __init__(self, debug: bool = False):
        self.debug = debug

    # def _get_runnable(self, state: RedboxState):
    #     settings = get_settings()
    #     llm = init_chat_model(
    #         model=state.chat_backend.name,
    #         model_provider=state.chat_backend.provider,
    #     )
    #
    #     input_state = state.model_dump()
    #     messages = (
    #         [settings.system_prompt_template]
    #         + state.messages[:-1]
    #         + PromptTemplate.from_template(settings.question_prompt_template, template_format="jinja2")
    #         .invoke(input=input_state)
    #         .to_messages()
    #     )
    #     return ChatPromptTemplate.from_messages(messages=messages) | llm

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

        server_params = StdioServerParameters(
            command="uv",
            args=[
                "--directory",
                "/Users/george.burton/caddy/model/caddy_model/",
                "run",
                "mcp",
                "run",
                "server.py"
            ],
        )
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                toolkit = MCPToolkit(session=session)
                await toolkit.initialize()

                tools = toolkit.get_tools()
                print(tools)

                llm = init_chat_model(
                    model=state.chat_backend.name,
                    model_provider=state.chat_backend.provider,
                )


                graph = create_react_agent(
                    llm,
                    tools=tools,
                )

                async for event in graph.astream_events(
                    state,
                    version="v2",
                ):
                    kind = event["event"]
                    if kind == "on_chat_model_stream":
                        content = event["data"]["chunk"].content
                        await response_tokens_callback(content)
                    elif kind == "on_chain_end":
                        final_state = event["data"]["output"]
        return final_state
