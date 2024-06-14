import logging
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, FastAPI, WebSocket
from fastapi.encoders import jsonable_encoder
from langchain_community.chat_models import ChatLiteLLM
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_elasticsearch import ElasticsearchStore

from core_api.src.auth import get_user_uuid, get_ws_user_uuid
from core_api.src.build_chains import build_retrieval_chain, build_summary_chain
from core_api.src.dependencies import get_llm, get_storage_handler, get_vector_store
from core_api.src.semantic_routes import (
    ABILITY_RESPONSE,
    COACH_RESPONSE,
    INFO_RESPONSE,
    route_layer,
)
from redbox.models.chat import ChatRequest, ChatResponse, ChatRoute, SourceDocument
from redbox.storage import ElasticsearchStorageHandler

# === Logging ===

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


chat_app = FastAPI(
    title="Core Chat API",
    description="Redbox Core Chat API",
    version="0.1.0",
    openapi_tags=[
        {"name": "chat", "description": "Chat interactions with LLM and RAG backend"},
        {
            "name": "embedding",
            "description": "Embedding interactions with SentenceTransformer",
        },
        {"name": "llm", "description": "LLM information and parameters"},
    ],
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

ROUTE_RESPONSES = {
    ChatRoute.info: ChatPromptTemplate.from_template(INFO_RESPONSE),
    ChatRoute.ability: ChatPromptTemplate.from_template(ABILITY_RESPONSE),
    ChatRoute.coach: ChatPromptTemplate.from_template(COACH_RESPONSE),
    ChatRoute.gratitude: ChatPromptTemplate.from_template("You're welcome!"),
    ChatRoute.retrieval: build_retrieval_chain,
    ChatRoute.summarisation: build_summary_chain,
    ChatRoute.extract: ChatPromptTemplate.from_template(
        "You asking to extract some information - route not yet implemented"
    ),
}


async def semantic_router_to_chain(
    chat_request: ChatRequest,
    user_uuid: UUID,
    llm: ChatLiteLLM,
    vector_store: ElasticsearchStore,
    storage_handler: ElasticsearchStorageHandler,
) -> tuple[Runnable, dict[str, Any], str]:
    question = chat_request.message_history[-1].text
    route = route_layer(question)

    if route_response := ROUTE_RESPONSES.get(route.name):
        if isinstance(route_response, ChatPromptTemplate):
            return route_response, {}, route.name
        if callable(route_response):
            chain, params = await route_response(
                chat_request=chat_request,
                user_uuid=user_uuid,
                llm=llm,
                vector_store=vector_store,
                storage_handler=storage_handler,
            )
            return chain, params, route.name

    chain, params = await build_retrieval_chain(chat_request, user_uuid, llm, vector_store)
    return chain, params, ChatRoute.vanilla


@chat_app.post("/rag", tags=["chat"])
async def rag_chat(
    chat_request: ChatRequest,
    user_uuid: Annotated[UUID, Depends(get_user_uuid)],
    llm: Annotated[ChatLiteLLM, Depends(get_llm)],
    vector_store: Annotated[ElasticsearchStore, Depends(get_vector_store)],
    storage_handler: Annotated[ElasticsearchStorageHandler, Depends(get_storage_handler)],
) -> ChatResponse:
    """REST endpoint.
    Chose the correct route based on the question.
    Get a response to a question history and file.
    """
    chain, params, route = await semantic_router_to_chain(chat_request, user_uuid, llm, vector_store, storage_handler)

    result = chain.invoke(params)
    if isinstance(result, dict):
        source_documents = [
            SourceDocument(
                page_content=document.page_content,
                file_uuid=document.metadata.get("parent_doc_uuid"),
                page_numbers=document.metadata.get("page_numbers"),
            )
            for document in result.get("input_documents", [])
        ]
        return ChatResponse(output_text=result["output_text"], source_documents=source_documents, route=route)
    # stuff_summarisation route
    elif isinstance(result, str):
        return ChatResponse(output_text=result, route=route)
    # hard-coded routes
    else:
        try:
            msg = result.messages[0].content
            return ChatResponse(output_text=msg, route=route)
        except (KeyError, AttributeError):
            logging.exception("unknown message format %s", str(result))


@chat_app.websocket("/rag")
async def rag_chat_streamed(
    websocket: WebSocket,
    llm: Annotated[ChatLiteLLM, Depends(get_llm)],
    vector_store: Annotated[ElasticsearchStore, Depends(get_vector_store)],
    storage_handler: Annotated[ElasticsearchStorageHandler, Depends(get_storage_handler)],
):
    """Websocket. Get a LLM response to a question history and file."""
    await websocket.accept()

    user_uuid = await get_ws_user_uuid(websocket)

    request = await websocket.receive_text()
    chat_request = ChatRequest.model_validate_json(request)

    chain, params, route = await semantic_router_to_chain(chat_request, user_uuid, llm, vector_store, storage_handler)

    async for event in chain.astream_events(params, version="v1"):
        kind = event["event"]
        if kind == "on_chat_model_stream":
            await websocket.send_json({"resource_type": "text", "data": event["data"]["chunk"].content})
        elif kind == "on_chat_model_end":
            await websocket.send_json({"resource_type": "end"})
        elif kind == "on_chain_stream":
            if isinstance(event["data"]["chunk"], dict):
                input_documents = event["data"]["chunk"].get("input_documents", [])
                source_documents = [
                    jsonable_encoder(
                        SourceDocument(
                            page_content=document.page_content,
                            file_uuid=document.metadata.get("parent_doc_uuid"),
                            page_numbers=document.metadata.get("page_numbers"),
                        )
                    )
                    for document in input_documents
                ]
                await websocket.send_json({"resource_type": "documents", "data": source_documents})
        elif kind == "on_prompt_stream":
            try:
                msg = event["data"]["chunk"].messages[0].content
                await websocket.send_json({"resource_type": "text", "data": msg})
            except (KeyError, AttributeError):
                logging.exception("unknown message format %s", str(event["data"]["chunk"]))
        elif kind == "on_chat_model_start":
            await websocket.send_json({"resource_type": "route", "route": route})

    await websocket.close()
