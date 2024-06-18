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
) -> tuple[Runnable, ChainInput, str]:
    question = chat_request.message_history[-1].text
    route = route_layer(question)

    selected_chain = routable_chains.get(route.name, routable_chains.get("retrieval"))
    params = ChainInput(
        question=chat_request.message_history[-1].text,
        file_uuids=[f.uuid for f in chat_request.selected_files],
        user_uuid=user_uuid,
        chat_history=chat_request.message_history[:-1],
    )
    return selected_chain, params, route.name


@chat_app.post("/rag", tags=["chat"])
async def rag_chat(
    chat_request: ChatRequest,
    user_uuid: Annotated[UUID, Depends(get_user_uuid)],
    routable_chains: Annotated[dict[str, Runnable], Depends(get_routable_chains)],
    route_layer: Annotated[RouteLayer, Depends(get_semantic_route_layer)],
) -> ChatResponse:
    """REST endpoint. Get a LLM response to a question history and file."""
    selected_chain, params, _ = await semantic_router_to_chain(chat_request, user_uuid, routable_chains, route_layer)
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

    selected_chain, params, route = await semantic_router_to_chain(
        chat_request, user_uuid, routable_chains, route_layer
    )

    streaming_routes = "retrieval", "summarisation"
    async for event in selected_chain.astream_events(params.model_dump(), version="v1"):
        kind = event["event"]
        if kind == "on_chat_model_stream" and route in streaming_routes:
            await websocket.send_json({"resource_type": "text", "data": event["data"]["chunk"].content, "route": route})
        elif kind == "on_chat_model_end":
            await websocket.send_json({"resource_type": "end", "route": route})
        elif kind == "on_chain_stream":
            if isinstance(event["data"]["chunk"], dict):
                source_chunks = event["data"]["chunk"].get("source_documents", [])
                source_documents = [
                    SourceDocument(
                        page_content=chunk.text,
                        file_uuid=chunk.parent_file_uuid,
                        page_numbers=chunk.metadata.page_number
                        if isinstance(chunk.metadata.page_number, list)
                        else [chunk.metadata.page_number]
                        if chunk.metadata.page_number
                        else [],
                    )
                    for chunk in source_chunks
                ]
                await websocket.send_json(
                    {
                        "resource_type": "documents",
                        "data": jsonable_encoder(list(set(source_documents))),
                        "route": route,
                    }
                )
        elif kind == "on_prompt_end" and route not in streaming_routes:
            try:
                msg = event["data"]["output"].messages[0].content
                await websocket.send_json({"resource_type": "text", "data": msg, "route": route})
            except (KeyError, AttributeError):
                logging.exception("unknown message format %s", str(event["data"]["output"]))

    await websocket.close()
