import logging
import re
from typing import Annotated, Literal
from uuid import UUID

from fastapi import Depends, FastAPI, WebSocket
from fastapi.encoders import jsonable_encoder
from langchain_core.runnables import Runnable
from openai import APIError
from pydantic import BaseModel
from semantic_router import RouteLayer

from core_api.src.auth import get_user_uuid, get_ws_user_uuid
from core_api.src.runnables import map_to_chat_response
from core_api.src.semantic_routes import get_routable_chains, get_semantic_route_layer
from redbox.models.chain import ChainInput
from redbox.models.chat import ChatRequest, ChatResponse, SourceDocument
from redbox.models.errors import NoDocumentSelected, QuestionLengthError
from redbox.transform import map_document_to_source_document

# === Logging ===

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()

re_keyword_pattern = re.compile(r"@(\w+)")


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
    user_uuid: UUID,
    routable_chains: dict[str, Runnable],
    route_layer: RouteLayer,
) -> tuple[Runnable, ChainInput]:
    question = chat_request.message_history[-1].text

    selected_chain = None

    # Match keyword
    route_match = re_keyword_pattern.search(question)
    if route_match:
        route_name = route_match.group()[1:]
        selected_chain = routable_chains.get(route_name)

    # Semantic route
    if selected_chain is None:
        route_name = route_layer(question).name
        selected_chain = routable_chains.get(route_name, routable_chains.get("search"))

    params = ChainInput(
        question=chat_request.message_history[-1].text,
        file_uuids=[f.uuid for f in chat_request.selected_files],
        user_uuid=user_uuid,
        chat_history=chat_request.message_history[:-1],
    )

    log.info("Routed to %s", route_name)

    return selected_chain, params


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


class ErrorDetail(BaseModel):
    code: str
    message: str


class ClientResponse(BaseModel):
    # Needs to match CoreChatResponse in django_app/redbox_app/redbox_core/consumers.py
    resource_type: Literal["text", "documents", "route_name", "end", "error"]
    data: list[SourceDocument] | str | ErrorDetail | None = None


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

    try:
        async for event in selected_chain.astream(params.model_dump()):
            response: str = event.get("response", "")
            source_documents: list[SourceDocument] = [
                map_document_to_source_document(doc) for doc in event.get("source_documents", [])
            ]
            route_name: str = event.get("route_name", "")
            if response:
                await send_to_client(ClientResponse(resource_type="text", data=response), websocket)
            if source_documents:
                await send_to_client(ClientResponse(resource_type="documents", data=source_documents), websocket)
            if route_name:
                await send_to_client(ClientResponse(resource_type="route_name", data=route_name), websocket)
    except NoDocumentSelected as e:
        log.info("No documents have been selected to summarise", exc_info=e)
        await send_to_client(
            ClientResponse(resource_type="error", data=ErrorDetail(code="no-document-selected", message=e.message)),
            websocket,
        )
    except QuestionLengthError as e:
        log.info("Question is too long", exc_info=e)
        await send_to_client(
            ClientResponse(resource_type="error", data=ErrorDetail(code="question-too-long", message=e.message)),
            websocket,
        )
    except APIError as e:
        log.exception("Unhandled exception.", exc_info=e)
        await send_to_client(
            ClientResponse(resource_type="error", data=ErrorDetail(code="unexpected", message=e.message)), websocket
        )
    finally:
        await send_to_client(ClientResponse(resource_type="end"), websocket)
        await websocket.close()


async def send_to_client(response: ClientResponse, websocket: WebSocket) -> None:
    await websocket.send_json(jsonable_encoder(response))
