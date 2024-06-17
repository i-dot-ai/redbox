import logging
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, WebSocket
from fastapi.encoders import jsonable_encoder
from langchain_core.runnables import Runnable
from semantic_router import RouteLayer

from core_api.src.auth import get_user_uuid, get_ws_user_uuid
from core_api.src.runnables import map_to_chat_response
from core_api.src.semantic_routes import get_routable_chains, get_semantic_route_layer
from redbox.models.chain import ChainInput
from redbox.models.chat import ChatRequest, ChatResponse, SourceDocument

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


async def semantic_router_to_chain(
    chat_request: ChatRequest, user_uuid: UUID, routable_chains: dict[str, Runnable], route_layer: RouteLayer
) -> tuple[Runnable, ChainInput]:
    question = chat_request.message_history[-1].text
    route = route_layer(question)

    selected_chain = routable_chains.get(route.name, routable_chains.get("retrieval"))
    params = ChainInput(
        question=chat_request.message_history[-1].text,
        file_uuids=[f.uuid for f in chat_request.selected_files],
        user_uuid=user_uuid,
        chat_history=chat_request.message_history[:-1],
    )
    return (selected_chain, params)


@chat_app.post("/rag", tags=["chat"])
async def rag_chat(
    chat_request: ChatRequest,
    user_uuid: Annotated[UUID, Depends(get_user_uuid)],
    routable_chains: Annotated[dict[str, Runnable], Depends(get_routable_chains)],
    route_layer: Annotated[RouteLayer, Depends(get_semantic_route_layer)],
) -> ChatResponse:
    """REST endpoint. Get a LLM response to a question history and file."""
    selected_chain, params = await semantic_router_to_chain(chat_request, user_uuid, routable_chains, route_layer)
    return (selected_chain | map_to_chat_response).invoke(params.model_dump())


@chat_app.websocket("/rag")
async def rag_chat_streamed(
    websocket: WebSocket,
    routable_chains: Annotated[dict[str, Runnable], Depends(get_routable_chains)],
    route_layer: Annotated[RouteLayer, Depends(get_semantic_route_layer)],
):
    """Websocket. Get a LLM response to a question history and file."""
    await websocket.accept()

    user_uuid = await get_ws_user_uuid(websocket)

    request = await websocket.receive_text()
    chat_request = ChatRequest.model_validate_json(request)

    selected_chain, params = await semantic_router_to_chain(chat_request, user_uuid, routable_chains, route_layer)

    async for event in selected_chain.astream_events(params.model_dump(), version="v1"):
        kind = event["event"]
        if kind == "on_chat_model_stream":
            await websocket.send_json({"resource_type": "text", "data": event["data"]["chunk"].content})
        elif kind == "on_chat_model_end":
            await websocket.send_json({"resource_type": "end"})
        elif kind == "on_chain_stream":
            if isinstance(event["data"]["chunk"], dict):
                source_chunks = event["data"]["chunk"].get("source_documents", [])
                source_documents = [
                    jsonable_encoder(
                        SourceDocument(
                            page_content=chunk.text,
                            file_uuid=chunk.parent_file_uuid,
                            page_numbers=[chunk.metadata.page_number],
                        )
                    )
                    for chunk in source_chunks
                ]
                await websocket.send_json({"resource_type": "documents", "data": source_documents})
        elif kind == "on_prompt_stream":
            try:
                msg = event["data"]["chunk"].messages[0].content
                await websocket.send_json({"resource_type": "text", "data": msg})
            except (KeyError, AttributeError):
                logging.exception("unknown message format %s", str(event["data"]["chunk"]))

    await websocket.close()
