from typing import Annotated

from core_api.build_chains import (
    build_chat_chain,
    build_chat_with_docs_chain,
    build_condense_retrieval_chain,
    build_static_response_chain,
)
from fastapi import Depends
from langchain_core.runnables import Runnable

from redbox.models.chat import ChatRoute
from redbox.models.chain import ChainInput

# === Pre-canned responses for non-LLM routes ===
INFO_RESPONSE = """
I am Redbox, an AI focused on helping UK Civil Servants, Political Advisors and
Ministers triage and summarise information from a wide variety of sources.
"""


def as_chat_tool(
    name: str,
    runnable: Runnable,
    description: str,
):
    return runnable.as_tool(name=name, description=description, args_schema=ChainInput)


__routable_chains = None


def get_routable_chains(
    condense_chain: Annotated[Runnable, Depends(build_condense_retrieval_chain)],
    chat_chain: Annotated[Runnable, Depends(build_chat_chain)],
    chat_with_docs_chain: Annotated[Runnable, Depends(build_chat_with_docs_chain)],
) -> dict[str, tuple[Runnable, str]]:
    global __routable_chains  # noqa: PLW0603
    if not __routable_chains:
        chat_tools = (
            (
                ChatRoute.info,
                build_static_response_chain(INFO_RESPONSE, ChatRoute.info),
                "Give helpful information about Redbox",
            ),
            (
                ChatRoute.chat,
                chat_chain,
                "Answer questions as a helpful assistant",
            ),
            (
                ChatRoute.chat_with_docs,
                chat_with_docs_chain,
                "Answer questions as a helpful assistant using the documents provided",
            ),
            (
                ChatRoute.search,
                condense_chain,
                "Search for an answer to a question in provided documents",
            ),
        )
        __routable_chains = {name: (runnable, description) for (name, runnable, description) in chat_tools}
    return __routable_chains
