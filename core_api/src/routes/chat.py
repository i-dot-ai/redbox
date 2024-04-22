from typing import List, Literal
from uuid import UUID

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from langchain.chains.llm import LLMChain
from langchain.chains.qa_with_sources import load_qa_with_sources_chain
from langchain_community.chat_models import ChatLiteLLM
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_elasticsearch import ElasticsearchStore, ApproxRetrievalStrategy
from typing_extensions import TypedDict

from redbox.llm.prompts.chat import (
    CONDENSE_QUESTION_PROMPT,
    STUFF_DOCUMENT_PROMPT,
    WITH_SOURCES_PROMPT,
)
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


# === LLM setup ===


llm = ChatLiteLLM(
    model="gpt-3.5-turbo",  # TODO: set with env var
    # TODO: set max_tokens and temperature
    streaming=True,
)

es = env.elasticsearch_client()
embedding_function = SentenceTransformerEmbeddings()
# TODO: do we want to be able to set hybrid to True depending on Elastic subscription levels?
# see: https://github.com/i-dot-ai/redbox-copilot-streamlit/blob/3d197e76e6d42cfe0b70f66bb374c899b74754b4/streamlit_app/utils.py#L316C17-L316C45
hybrid = True
strategy = ApproxRetrievalStrategy(hybrid=hybrid)

# TODO: fix this - I don't think it's correctly implemented, as we're getting an error when making a request:
# raise HTTP_EXCEPTIONS.get(meta.status, ApiError)(
# elasticsearch.NotFoundError: NotFoundError(404, 'status_exception', '[file] is not an inference service model or a deployed ml model')
vector_store = ElasticsearchStore(
    es_connection=es,
    index_name="redbox-data-chunk",
    embedding=embedding_function,
    strategy=strategy,
    vector_query_field="embedding",
)


# TODO: decide what we're doing with our backend ChatMessage class
class ChatMessage(TypedDict):
    text: str
    role: Literal["user", "ai", "system"]


@chat_app.post("/vanilla", tags=["chat"])
def simple_chat(chat_history: List[ChatMessage]) -> StreamingResponse:
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

    if len(chat_history) < 2:
        raise HTTPException(
            status_code=422,
            detail="Chat history should include both system and user prompts",
        )

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


@chat_app.post("/rag", tags=["chat"])
def rag_chat(chat_history: List[ChatMessage], files: List[UUID]) -> str:
    """Get a LLM response to a question history and file

    Args:


    Returns:
        StreamingResponse: a stream of the chain response
    """
    question = chat_history[-1]
    previous_history = chat_history[0:-1]

    docs_with_sources_chain = load_qa_with_sources_chain(
        llm,
        chain_type="stuff",
        prompt=WITH_SOURCES_PROMPT,
        document_prompt=STUFF_DOCUMENT_PROMPT,
        verbose=True,
    )

    condense_question_chain = LLMChain(llm=llm, prompt=CONDENSE_QUESTION_PROMPT)

    # split chain manually, so that the standalone question doesn't leak into chat
    standalone_question = condense_question_chain({"question": question, "chat_history": previous_history})["text"]

    # TODO: limit this to the user provided documents
    # also, this is currently causing a 404 error (see error in note line 52)
    docs = vector_store.as_retriever().get_relevant_documents(standalone_question)

    result = docs_with_sources_chain(
        {
            "question": standalone_question,
            "input_documents": docs,
        },
    )

    return result["output_text"]
