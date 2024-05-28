import logging
from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, WebSocket
from fastapi.encoders import jsonable_encoder
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains.history_aware_retriever import create_history_aware_retriever
from langchain.chains.retrieval import create_retrieval_chain
from langchain_community.chat_models import ChatLiteLLM
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import Runnable
from langchain_elasticsearch import ApproxRetrievalStrategy, ElasticsearchStore

from core_api.src.auth import get_user_uuid
from redbox.llm.prompts.chat import (
    CONDENSE_QUESTION_TEMPLATE,
    CORE_REDBOX_TEMPLATE,
    WITH_SOURCES_TEMPLATE,
)
from redbox.model_db import MODEL_PATH
from redbox.models import EmbeddingModelInfo, Settings
from redbox.models.chat import ChatMessage, ChatRequest, ChatResponse, SourceDocument

# === Logging ===

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()

env = Settings()


chat_app = FastAPI(
    title="Core Chat API",
    description="Redbox Core Chat API",
    version="0.1.0",
    openapi_tags=[
        {"name": "chat", "description": "Chat interactions with LLM and RAG backend"},
        {"name": "embedding", "description": "Embedding interactions with SentenceTransformer"},
        {"name": "llm", "description": "LLM information and parameters"},
    ],
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

log.info("Loading embedding model from environment: %s", env.embedding_model)
embedding_model = SentenceTransformerEmbeddings(model_name=env.embedding_model, cache_folder=MODEL_PATH)
log.info("Loaded embedding model from environment: %s", env.embedding_model)


def populate_embedding_model_info() -> EmbeddingModelInfo:
    test_text = "This is a test sentence."
    embedding = embedding_model.embed_documents([test_text])[0]
    return EmbeddingModelInfo(
        embedding_model=env.embedding_model,
        vector_size=len(embedding),
    )


embedding_model_info = populate_embedding_model_info()


# === LLM setup ===


llm = ChatLiteLLM(
    model="gpt-3.5-turbo",
    streaming=True,
)

es = env.elasticsearch_client()
if env.elastic.subscription_level == "basic":
    strategy = ApproxRetrievalStrategy(hybrid=False)
elif env.elastic.subscription_level in ["platinum", "enterprise"]:
    strategy = ApproxRetrievalStrategy(hybrid=True)
else:
    message = f"Unknown Elastic subscription level {env.elastic.subscription_level}"
    raise ValueError(message)


vector_store = ElasticsearchStore(
    es_connection=es,
    index_name="redbox-data-chunk",
    embedding=embedding_model,
    strategy=strategy,
    vector_query_field="embedding",
)


@chat_app.post("/vanilla", tags=["chat"], response_model=ChatResponse)
def simple_chat(chat_request: ChatRequest, _user_uuid: Annotated[UUID, Depends(get_user_uuid)]) -> ChatResponse:
    """Get a LLM response to a question history"""

    if len(chat_request.message_history) < 2:
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            detail="Chat history should include both system and user prompts",
        )

    if chat_request.message_history[0].role != "system":
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            detail="The first entry in the chat history should be a system prompt",
        )

    if chat_request.message_history[-1].role != "user":
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            detail="The final entry in the chat history should be a user question",
        )

    chat_prompt = ChatPromptTemplate.from_messages((msg.role, msg.text) for msg in chat_request.message_history)
    # Convert to LangChain style messages
    messages = chat_prompt.format_messages()

    response = llm(messages)

    return ChatResponse(response_message=ChatMessage(text=response.text, role="ai"))


@chat_app.post("/rag", tags=["chat"])
def rag_chat(chat_request: ChatRequest, user_uuid: Annotated[UUID, Depends(get_user_uuid)]) -> ChatResponse:
    """Get a LLM response to a question history and file

    Args:

    Returns:
        StreamingResponse: a stream of the chain response
    """
    retrieval_chain = build_retrieval_chain(user_uuid)

    chat = get_chat_from_request(chat_request)

    result = retrieval_chain.invoke(chat)

    source_documents = [
        SourceDocument(
            page_content=langchain_document.page_content,
            file_uuid=langchain_document.metadata.get("parent_doc_uuid"),
            page_numbers=langchain_document.metadata.get("page_numbers"),
        )
        for langchain_document in result.get("context", [])
    ]
    return ChatResponse(output_text=result["answer"], source_documents=source_documents)


@chat_app.websocket("/rag")
async def rag_chat_streamed(websocket: WebSocket):
    await websocket.accept()

    chat_request = ChatRequest.parse_raw(await websocket.receive_text())

    retrieval_chain = build_retrieval_chain()

    chat = get_chat_from_request(chat_request)

    async for event in retrieval_chain.astream_events(chat, version="v1"):
        kind = event["event"]
        if kind == "on_chat_model_stream":
            await websocket.send_json({"resource_type": "text", "data": event["data"]["chunk"].content})
        elif kind == "on_chat_model_end":
            await websocket.send_json({"resource_type": "end"})
        elif kind == "on_retriever_end":
            source_documents = [
                jsonable_encoder(
                    SourceDocument(
                        page_content=document.page_content,
                        file_uuid=document.metadata.get("parent_doc_uuid"),
                        page_numbers=document.metadata.get("page_numbers"),
                    )
                )
                for document in event["data"]["output"]["documents"]
            ]
            await websocket.send_json({"resource_type": "documents", "data": source_documents})

    await websocket.close()


def build_retrieval_chain(user_uuid: UUID | None = None) -> Runnable:
    prompt_search_query = ChatPromptTemplate.from_messages(
        [
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "{input}"),
            (
                "user",
                CONDENSE_QUESTION_TEMPLATE,
            ),
        ]
    )
    search_kwargs = {"filter": {"term": {"creator_user_uuid.keyword": str(user_uuid)}}} if user_uuid else {}

    retriever_chain = create_history_aware_retriever(
        llm,
        vector_store.as_retriever(search_kwargs=search_kwargs),
        prompt_search_query,
    )
    prompt_get_answer = ChatPromptTemplate.from_messages(
        [
            ("system", CORE_REDBOX_TEMPLATE + WITH_SOURCES_TEMPLATE),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "{input}"),
        ]
    )
    document_chain = create_stuff_documents_chain(llm, prompt_get_answer)
    return create_retrieval_chain(retriever_chain, document_chain)


def get_chat_from_request(chat_request: ChatRequest) -> dict:
    chat_history = [
        HumanMessage(content=x.text) if x.role == "user" else AIMessage(content=x.text)
        for x in chat_request.message_history[:-1]
    ]
    return {"chat_history": chat_history, "input": chat_request.message_history[-1].text}
