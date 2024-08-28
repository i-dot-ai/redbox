import json
import logging
from asyncio import CancelledError
from collections.abc import Mapping, MutableSequence, Sequence
from dataclasses import dataclass
from typing import Any, Literal
from uuid import UUID

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from dataclasses_json import Undefined, dataclass_json
from django.conf import settings
from django.forms.models import model_to_dict
from django.utils import timezone
from websockets import ConnectionClosedError, WebSocketClientProtocol
from websockets.client import connect
from yarl import URL

from redbox_app.redbox_core import error_messages
from redbox_app.redbox_core.models import AISettings, Chat, ChatMessage, ChatRoleEnum, Citation, File, User

OptFileSeq = Sequence[File] | None
logger = logging.getLogger(__name__)
logger.info("WEBSOCKET_SCHEME is: %s", settings.WEBSOCKET_SCHEME)


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass(frozen=True)
class CoreChatResponseDoc:
    file_uuid: UUID
    page_content: str | None = None
    page_numbers: list[int] | None = None


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass(frozen=True)
class ErrorDetail:
    code: str
    message: str


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass(frozen=True)
class CoreChatResponse:
    # Needs to be a subset of ClientResponse in core_api/src/routes/chat.py
    resource_type: Literal["text", "documents", "route_name", "end", "error"]
    data: list[CoreChatResponseDoc] | str | ErrorDetail | None = None


class ChatConsumer(AsyncWebsocketConsumer):
    async def receive(self, text_data=None, bytes_data=None):
        """Receive & respond to message from browser websocket."""
        data = json.loads(text_data or bytes_data)
        logger.debug("received %s from browser", data)
        user_message_text: str = data.get("message", "")

        selected_file_uuids: Sequence[UUID] = [UUID(u) for u in data.get("selectedFiles", [])]
        user: User = self.scope.get("user", None)

        if session_id := data.get("sessionId"):
            chat = await Chat.objects.aget(id=session_id)
        else:
            chat = await Chat.objects.acreate(name=user_message_text[0 : settings.CHAT_TITLE_LENGTH], user=user)

        # save user message
        message = await ChatMessage.objects.acreate(chat=chat, text=user_message_text, role=ChatRoleEnum.user)
        async for file in File.objects.filter(id__in=selected_file_uuids, user=user):
            message.selected_files.add(file)

        await self.llm_conversation(message, user)
        await self.close()

    async def llm_conversation(self, chat_message: ChatMessage, user: User) -> None:
        """Initiate & close websocket conversation with the core-api message endpoint."""

        message_history: Sequence[Mapping[str, str]] = [
            {"role": message.role, "text": message.text}
            async for message in ChatMessage.objects.filter(chat=chat_message.chat).order_by("created_at")
        ]
        url = URL.build(scheme="ws", host=settings.CORE_API_HOST, port=settings.CORE_API_PORT) / "chat/rag"
        try:
            async with connect(str(url), extra_headers={"Authorization": user.get_bearer_token()}) as core_websocket:
                message = {
                    "message_history": message_history,
                    "selected_files": [{"uuid": f.core_file_uuid} async for f in chat_message.selected_files.all()],
                    "ai_settings": await self.get_ai_settings(user),
                }
                await self.send_to_server(core_websocket, message)
                await self.send_to_client("session-id", chat_message.chat.id)
                reply, files_and_citations, route = await self.receive_llm_responses(user, core_websocket)
                for file, _ in files_and_citations:
                    await self.send_to_client(
                        "source", {"url": str(file.url), "original_file_name": file.original_file_name}
                    )

            chat_message = await ChatMessage.objects.acreate(
                chat=chat_message.chat, text=reply, role=ChatRoleEnum.ai, route=route
            )

            for file, citations in files_and_citations:
                file.last_referenced = timezone.now()
                await file.asave()
                for citation in citations:
                    await Citation.objects.acreate(
                        chat_message=chat_message,
                        file=file,
                        text=citation.page_content,
                        page_numbers=citation.page_numbers,
                    )

            await self.send_to_client(
                "end",
                {
                    "message_id": chat_message.id,
                    "title": chat_message.text,
                    "session_id": chat_message.chat.id,
                },
            )
        except RateLimitError as e:
            logger.exception("429 error from core.", exc_info=e)
            await self.send_to_client("error", error_messages.RATE_LIMITED)

        except (TimeoutError, ConnectionClosedError, CancelledError, CoreError) as e:
            logger.exception("Error from core.", exc_info=e)
            await self.send_to_client("error", error_messages.CORE_ERROR_MESSAGE)

    async def receive_llm_responses(
        self, user: User, core_websocket: WebSocketClientProtocol
    ) -> tuple[str, Sequence[tuple[File, CoreChatResponseDoc]], str]:
        """Conduct websocket conversation with the core-api message endpoint."""
        full_reply: MutableSequence[str] = []
        citations: MutableSequence[tuple[File, CoreChatResponseDoc]] = []
        route: str | None = None
        async for raw_message in core_websocket:
            response: CoreChatResponse = CoreChatResponse.schema().loads(raw_message)
            logger.debug("received %s from core-api", response)
            if response.resource_type == "text":
                full_reply.append(await self.handle_text(response))
            elif response.resource_type == "documents":
                citations += await self.handle_documents(response, user)
            elif response.resource_type == "route_name":
                route = await self.handle_route(response, user.is_staff)
            elif response.resource_type == "error":
                full_reply.append(await self.handle_error(response))
        return "".join(full_reply), citations, route

    async def handle_documents(
        self, response: CoreChatResponse, user: User
    ) -> Sequence[tuple[File, CoreChatResponseDoc]]:
        """this function enriches the citations received from the core-api with
        the matching djangio File objects."""
        docs = response.data

        return [
            (file, [doc for doc in docs if doc.file_uuid == file.core_file_uuid])
            async for file in File.objects.filter(core_file_uuid__in=[doc.file_uuid for doc in docs], user=user)
        ]

    async def handle_text(self, response: CoreChatResponse) -> str:
        await self.send_to_client("text", response.data)
        return response.data

    async def handle_route(self, response: CoreChatResponse, show_route: bool) -> str:
        # TODO(@rachaelcodes): remove is_staff conditional and hidden-route with new route design
        # https://technologyprogramme.atlassian.net/browse/REDBOX-419
        if show_route:
            await self.send_to_client("route", response.data)
        else:
            await self.send_to_client("hidden-route", response.data)
        return response.data

    async def handle_error(self, response: CoreChatResponse) -> str:
        match response.data.code:
            case "no-document-selected":
                message = error_messages.SELECT_DOCUMENT
                await self.send_to_client("text", message)
                return message
            case "question-too-long":
                message = error_messages.QUESTION_TOO_LONG
                await self.send_to_client("text", message)
                return message
            case "rate-limit":
                message = f"{response.data.code}: {response.data.message}"
                raise RateLimitError(message)
            case _:
                message = f"{response.data.code}: {response.data.message}"
                raise CoreError(message)

    async def send_to_client(self, message_type: str, data: str | Mapping[str, Any] | None = None) -> None:
        message = {"type": message_type, "data": data}
        logger.debug("sending %s to browser", message)
        await self.send(json.dumps(message, default=str))

    @staticmethod
    async def send_to_server(websocket: WebSocketClientProtocol, data: Mapping[str, Any]) -> None:
        logger.debug("sending %s to core-api", data)
        return await websocket.send(json.dumps(data, default=str))

    @staticmethod
    @database_sync_to_async
    def get_ai_settings(user: User) -> AISettings:
        return model_to_dict(
            user.ai_settings,
            fields=[field.name for field in user.ai_settings._meta.fields if field.name != "label"],  # noqa: SLF001
        )


class CoreError(Exception):
    message: str


class RateLimitError(CoreError):
    pass
