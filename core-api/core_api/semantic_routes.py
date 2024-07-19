from typing import Annotated
from uuid import UUID

from core_api.build_chains import (
    build_chat_chain,
    build_chat_with_docs_chain,
    build_condense_retrieval_chain,
    build_static_response_chain,
)
from core_api.dependencies import get_env
from fastapi import Depends
from langchain_core.runnables import Runnable
from langchain_community.tools import Tool
from semantic_router import Route
from semantic_router.encoders import AzureOpenAIEncoder, BaseEncoder, OpenAIEncoder
from semantic_router.layer import RouteLayer

from redbox.models import Settings
from redbox.models.chat import ChatRoute, ChatMessage
from redbox.models.chain import ChainInput

# === Pre-canned responses for non-LLM routes ===
INFO_RESPONSE = """
I am Redbox, an AI focused on helping UK Civil Servants, Political Advisors and
Ministers triage and summarise information from a wide variety of sources.
"""

ABILITY_RESPONSE = """
* I can help you search over selected documents and do Q&A on them.
* I can help you summarise selected documents.
* I can help you extract information from selected documents.
* I can return information in a variety of formats, such as bullet points.
"""

COACH_RESPONSE = """
I am sorry that didn't work.
You could try rephrasing your task, i.e if you want to summarise a document please use the term,
"Summarise the selected document" or "extract all action items from the selected document."
If you want the results to be returned in a specific format, please specify the format in as much detail as possible.
"""

# === Set up the semantic router ===
info = Route(
    name=ChatRoute.info.value,
    utterances=[
        "What is your name?",
        "Who are you?",
        "What is Redbox?",
    ],
)

ability = Route(
    name=ChatRoute.ability.value,
    utterances=[
        "What can you do?",
        "What can you do?",
        "How can you help me?",
        "What does Redbox do?",
        "What can Redbox do",
        "What don't you do",
        "Please help me",
        "Please help",
        "Help me!",
        "help",
    ],
)

coach = Route(
    name=ChatRoute.coach.value,
    utterances=[
        "That is not the answer I wanted",
        "Rubbish",
        "No good",
        "That's not what I wanted",
        "How can I improve the results?",
    ],
)

gratitude = Route(
    name=ChatRoute.gratitude.value,
    utterances=[
        "Thank you",
        "Thank you ever so much for your help!",
        "I'm really grateful for your assistance.",
        "Cheers for the detailed response!",
        "Thanks a lot, that was very informative.",
        "Nice one",
        "Thanks!",
    ],
)

__routable_chains = None
__semantic_route_layer = None


def get_semantic_routes():
    return (info, ability, coach, gratitude)


def get_semantic_routing_encoder(env: Annotated[Settings, Depends(get_env)]):
    """
    TODO: This is a duplication of the logic for getting the LangChain embedding model used elsewhere
    We should replace semanticrouter with our own implementation to avoid this
    """
    if env.embedding_backend == "azure":
        return AzureOpenAIEncoder(
            azure_endpoint=env.azure_openai_endpoint, api_version="2023-05-15", model=env.azure_embedding_model
        )
    elif env.embedding_backend == "openai":
        return OpenAIEncoder(
            openai_base_url=env.embedding_openai_base_url,
            openai_api_key=env.openai_api_key,
            name=env.embedding_openai_model,
        )


def get_semantic_route_layer(
    routes: Annotated[list[Route], Depends(get_semantic_routes)],
    encoder: Annotated[BaseEncoder, Depends(get_semantic_routing_encoder)],
):
    """
    Manual singleton creation as lru_cache can't handle the semantic router classes (non hashable)
    """
    global __semantic_route_layer  # noqa: PLW0603
    if not __semantic_route_layer:
        __semantic_route_layer = RouteLayer(encoder=encoder, routes=routes)
    return __semantic_route_layer


def as_chat_tool(
        name: str,
        runnable: Runnable,
        description: str,
):
    return runnable.as_tool(
        name=name,
        description=description,
        args_schema=ChainInput
    )

def get_routable_chains(
    condense_chain: Annotated[Runnable, Depends(build_condense_retrieval_chain)],
    chat_chain: Annotated[Runnable, Depends(build_chat_chain)],
    chat_with_docs_chain: Annotated[Runnable, Depends(build_chat_with_docs_chain)],
) -> dict[str, Tool]:
    global __routable_chains  # noqa: PLW0603
    if not __routable_chains:
        chat_tools = (
            as_chat_tool(
                name=ChatRoute.info,
                runnable=build_static_response_chain(INFO_RESPONSE, ChatRoute.info),
                description="Give helpful information about Redbox",
            ),
            as_chat_tool(
                name=ChatRoute.ability,
                runnable=build_static_response_chain(ABILITY_RESPONSE, ChatRoute.ability),
                description="Describe what Redbox can do",
            ),
            as_chat_tool(
                name=ChatRoute.coach,
                runnable=build_static_response_chain(COACH_RESPONSE, ChatRoute.coach),
                description="Help users to use Redbox well",
            ),
            as_chat_tool(
                name=ChatRoute.gratitude,
                runnable=build_static_response_chain("You're welcome!", ChatRoute.gratitude),
                description="Respond to thanks",
            ),
            as_chat_tool(
                name=ChatRoute.chat,
                runnable=chat_chain,
                description="Answer questions as a helpful assistant",
            ),
            as_chat_tool(
                name=ChatRoute.chat_with_docs,
                runnable=chat_with_docs_chain,
                description="Answer questions as a helpful assistant using the documents provided",
            ),
            as_chat_tool(
                name=ChatRoute.search,
                runnable=condense_chain,
                description="Search for an answer to a question in provided documents",
            )
        )
        __routable_chains = {
            chat_tool.name: chat_tool
            for chat_tool in chat_tools
        }
    return __routable_chains
