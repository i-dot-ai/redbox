import logging
from typing import Annotated, Any, Dict
from uuid import UUID

from fastapi import Depends, FastAPI, WebSocket
from fastapi.encoders import jsonable_encoder
from langchain_community.chat_models import ChatLiteLLM
from langchain_core.runnables import Runnable
from langchain_elasticsearch import ElasticsearchStore
from langchain_core.prompts import ChatPromptTemplate

from core_api.src.auth import get_user_uuid, get_ws_user_uuid
from core_api.src.build_chains import build_retrieval_chain, build_summary_chain, get_routable_chains
from core_api.src.dependencies import get_llm, get_storage_handler, get_vector_store, get_es_retriever
from core_api.src.runnables import map_to_chat_response, make_static_response_chain
from redbox.llm.prompts.chat import RETRIEVAL_SYSTEM_PROMPT_TEMPLATE, RETRIEVAL_QUESTION_PROMPT_TEMPLATE
from redbox.llm.prompts.summarisation import SUMMARISATION_SYSTEM_PROMPT_TEMPLATE, SUMMARISATION_QUESTION_PROMPT_TEMPLATE
from core_api.src.semantic_routes import route_layer
from redbox.models.chain import ChainInput
from redbox.models.chat import ChatRequest, ChatResponse, SourceDocument
from redbox.storage import ElasticsearchStorageHandler
from core_api.src.semantic_routes import (
    ABILITY_RESPONSE,
    COACH_RESPONSE,
    INFO_RESPONSE,
)

# === Logging ===

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()

ROUTABLE_CHAINS = {
    "info": make_static_response_chain(INFO_RESPONSE),
    "ability": make_static_response_chain(ABILITY_RESPONSE),
    "coach": make_static_response_chain(COACH_RESPONSE),
    "gratitude": make_static_response_chain("You're welcome!"),
    "retrieval": build_retrieval_chain(get_llm, get_es_retriever, RETRIEVAL_SYSTEM_PROMPT_TEMPLATE, RETRIEVAL_QUESTION_PROMPT_TEMPLATE),
    "summarisation": build_summary_chain(get_llm, get_es_retriever, SUMMARISATION_SYSTEM_PROMPT_TEMPLATE, SUMMARISATION_QUESTION_PROMPT_TEMPLATE),
    "extract": make_static_response_chain("You asking to extract some information - route not yet implemented")
}

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

async def semantic_router_to_chain(
    chat_request: ChatRequest,
    user_uuid: UUID
) -> tuple[Runnable, ChainInput]:
    question = chat_request.message_history[-1].text
    route = route_layer(question)

    selected_chain = ROUTABLE_CHAINS.get(route.name, ROUTABLE_CHAINS.get('retrieval'))
    params = ChainInput(
        question=chat_request.message_history[-1].text,
        file_uuids=[f.uuid for f in chat_request.selected_files],
        user_uuid=user_uuid,
        chat_history=chat_request.message_history[:-1]
    )
    return (selected_chain, params)


@chat_app.post("/rag", tags=["chat"])
async def rag_chat(
    chat_request: ChatRequest,
    user_uuid: Annotated[UUID, Depends(get_user_uuid)]
) -> ChatResponse:
    """REST endpoint. Get a LLM response to a question history and file."""
    selected_chain, params = await semantic_router_to_chain(chat_request, user_uuid)
    return (selected_chain | map_to_chat_response).invoke(params.model_dump())


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

    selected_chain, params = await semantic_router_to_chain(chat_request, user_uuid)

    async for event in selected_chain.astream_events(params, version="v1"):
        kind = event["event"]
        if kind == "on_chat_model_stream":
            await websocket.send_json({"resource_type": "text", "data": event["data"]["chunk"].content})
        elif kind == "on_chat_model_end":
            await websocket.send_json({"resource_type": "end"})
        elif kind == "on_chain_stream":
            if isinstance(event["data"]["chunk"], dict):
                input_documents = event["data"]["chunk"].get("source_documents", [])
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

    await websocket.close()
