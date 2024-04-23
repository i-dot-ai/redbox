from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from langchain.chains.llm import LLMChain
from langchain_community.chat_models import ChatLiteLLM
from langchain_core.prompts import ChatPromptTemplate
from pydantic import conlist
from typing_extensions import TypedDict

from redbox.models import Settings

env = Settings()


chat_app = FastAPI(
    title="Core Chat API",
    description="Redbox Core Chat API",
    version="0.1.0",
    openapi_tags=[
        {"name": "chat", "description": "Chat endpoints"},
    ],
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


llm = ChatLiteLLM(
    model="gpt-3.5-turbo",  # TODO: set with env var
    # TODO: set max_tokens and temperature
    streaming=True,
)


# TODO: decide what we're doing with our backend ChatMessage class
class ChatMessage(TypedDict):
    text: str
    role: Literal["user", "ai", "system"]


@chat_app.post("/vanilla", tags=["chat"])
def simple_chat(chat_history: conlist(ChatMessage, min_length=2)) -> StreamingResponse:
    """Get a LLM response to a question history

    Args:
        chat_history ([{
            text (str): the prompt text
            role (Literal["user", "ai", "system"])
        }]): a List containing the full chat history

    The first chat_history object should be the "system" prompt.
    The final chat_history object should be the "user" question.

    Returns:
        StreamingResponse: a stream of the chain response
    """

    if chat_history[0]["role"] != "system":
        raise HTTPException(
            status_code=422,
            detail="The first entry in the chat history should be a system prompt",
        )

    if chat_history[-1]["role"] != "user":
        raise HTTPException(
            status_code=422,
            detail="The final entry in the chat history should be a user question",
        )

    # TODO: handle errors from LLM request
    # maybe litellm.exceptions.APIError: OpenAIException?

    question = chat_history[-1]
    previous_history = chat_history[0:-1]

    chat_prompt = ChatPromptTemplate.from_messages((msg["role"], msg["text"]) for msg in previous_history)

    chain = LLMChain(llm=llm, prompt=chat_prompt)

    return chain.stream({"input": question["text"]})
