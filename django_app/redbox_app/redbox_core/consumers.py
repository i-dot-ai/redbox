import json
import logging
from asyncio import CancelledError
from collections.abc import Mapping, MutableSequence, Sequence
from typing import Any
from uuid import UUID

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
from django.forms.models import model_to_dict
from django.utils import timezone
from websockets import ConnectionClosedError, WebSocketClientProtocol
from websockets.client import connect
from yarl import URL

from redbox.models.chat import ClientResponse, MetadataDetail, SourceDocument
from redbox_app.redbox_core import error_messages
from redbox_app.redbox_core.models import (
    AISettings,
    Chat,
    ChatMessage,
    ChatMessageTokenUse,
    ChatRoleEnum,
    Citation,
    File,
    User,
)

OptFileSeq = Sequence[File] | None
logger = logging.getLogger(__name__)
logger.info("WEBSOCKET_SCHEME is: %s", settings.WEBSOCKET_SCHEME)


class ChatConsumer(AsyncWebsocketConsumer):
    async def receive(self, text_data=None, bytes_data=None):
        """Receive & respond to message from browser websocket."""
        data = json.loads(text_data or bytes_data)
        logger.debug("received %s from browser", data)
        user_message_text: str = data.get("message", "")
        session_id: str | None = data.get("sessionId", None)
        selected_file_uuids: Sequence[UUID] = [UUID(u) for u in data.get("selectedFiles", [])]
        user: User = self.scope.get("user", None)

        session: Chat = await self.get_session(session_id, user, user_message_text)

        # save user message
        selected_files = File.objects.filter(id__in=selected_file_uuids, user=user)
        await self.save_message(session, user_message_text, ChatRoleEnum.user, selected_files=selected_files)

        await self.llm_conversation(selected_files, session, user, user_message_text)
        await self.close()

    async def llm_conversation(self, selected_files: Sequence[File], session: Chat, user: User, title: str) -> None:
        """Initiate & close websocket conversation with the core-api message endpoint."""
        session_messages = ChatMessage.objects.filter(chat=session).order_by("created_at")
        message_history: Sequence[Mapping[str, str]] = [
            {"role": message.role, "text": message.text} async for message in session_messages
        ]
        url = URL.build(scheme="ws", host=settings.CORE_API_HOST, port=settings.CORE_API_PORT) / "chat/rag"
        try:
            async with connect(str(url), extra_headers={"Authorization": user.get_bearer_token()}) as core_websocket:
                message = {
                    "message_history": message_history,
                    "selected_files": [{"s3_key": f.unique_name} for f in selected_files],
                    "ai_settings": await self.get_ai_settings(user),
                }
                await self.send_to_server(core_websocket, message)
                await self.send_to_client("session-id", session.id)
                reply, citations, route, metadata = await self.receive_llm_responses(user, core_websocket)
            message = await self.save_message(
                session, reply, ChatRoleEnum.ai, sources=citations, route=route, metadata=metadata
            )
            await self.send_to_client("end", {"message_id": message.id, "title": title, "session_id": session.id})

            for file, _ in citations:
                file.last_referenced = timezone.now()
                await file.asave()

        except RateLimitError as e:
            logger.exception("429 error from core.", exc_info=e)
            await self.send_to_client("error", error_messages.RATE_LIMITED)
        except (TimeoutError, ConnectionClosedError, CancelledError, CoreError) as e:
            logger.exception("Error from core.", exc_info=e)
            await self.send_to_client("error", error_messages.CORE_ERROR_MESSAGE)

    async def receive_llm_responses(
        self, user: User, core_websocket: WebSocketClientProtocol
    ) -> tuple[str, Sequence[tuple[File, SourceDocument]], str, MetadataDetail]:
        """Conduct websocket conversation with the core-api message endpoint."""
        full_reply: MutableSequence[str] = []
        citations: MutableSequence[tuple[File, SourceDocument]] = []
        route: str | None = None
        metadata: MetadataDetail = MetadataDetail()
        async for raw_message in core_websocket:
            response: ClientResponse = ClientResponse.model_validate_json(raw_message)
            logger.debug("received %s from core-api", response)
            if response.resource_type == "text":
                full_reply.append(await self.handle_text(response))
            elif response.resource_type == "documents":
                citations += await self.handle_documents(response)
            elif response.resource_type == "route_name":
                route = await self.handle_route(response, user.is_staff)
            elif response.resource_type == "metadata":
                metadata = await self.handle_metadata(metadata, response.data)
            elif response.resource_type == "error":
                full_reply.append(await self.handle_error(response))
        return "".join(full_reply), citations, route, metadata

    async def handle_documents(self, response: ClientResponse) -> Sequence[tuple[File, SourceDocument]]:
        s3_keys = [doc.s3_key for doc in response.data]
        files = File.objects.filter(original_file__in=s3_keys)

        async for file in files:
            await self.send_to_client("source", {"url": str(file.url), "original_file_name": file.original_file_name})

        return [(file, [doc for doc in response.data if doc.s3_key == file.unique_name]) for file in files]

    async def handle_text(self, response: ClientResponse) -> str:
        await self.send_to_client("text", response.data)
        return response.data

    async def handle_route(self, response: ClientResponse, show_route: bool) -> str:
        # TODO(@rachaelcodes): remove is_staff conditional and hidden-route with new route design
        # https://technologyprogramme.atlassian.net/browse/REDBOX-419
        if show_route:
            await self.send_to_client("route", response.data)
        else:
            await self.send_to_client("hidden-route", response.data)
        return response.data

    async def handle_metadata(self, current_metadata: MetadataDetail, metadata_event: MetadataDetail):
        result = current_metadata.model_copy(deep=True)
        for model, token_count in metadata_event.input_tokens.items():
            result.input_tokens[model] = current_metadata.input_tokens.get(model, 0) + token_count
        for model, token_count in metadata_event.output_tokens.items():
            result.output_tokens[model] = current_metadata.output_tokens.get(model, 0) + token_count
        return result

    async def handle_error(self, response: ClientResponse) -> str:
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
    def get_session(session_id: str, user: User, user_message_text: str) -> Chat:
        if session_id:
            session = Chat.objects.get(id=session_id)
        else:
            session_name = user_message_text[0 : settings.CHAT_TITLE_LENGTH]
            session = Chat(name=session_name, user=user)
            session.save()
        return session

    @staticmethod
    @database_sync_to_async
    def save_message(
        session: Chat,
        user_message_text: str,
        role: ChatRoleEnum,
        sources: Sequence[tuple[File, SourceDocument]] | None = None,
        selected_files: Sequence[File] | None = None,
        metadata: MetadataDetail | None = None,
        route: str | None = None,
    ) -> ChatMessage:
        chat_message = ChatMessage(chat=session, text=user_message_text, role=role, route=route)
        chat_message.save()
        if sources:
            for file, citations in sources:
                file.last_referenced = timezone.now()
                file.save()

                for citation in citations:
                    Citation.objects.create(
                        chat_message=chat_message,
                        file=file,
                        text=citation.page_content,
                        page_numbers=citation.page_numbers,
                    )
        if selected_files:
            chat_message.selected_files.set(selected_files)

        if metadata and metadata.input_tokens:
            for model, token_count in metadata.input_tokens.items():
                ChatMessageTokenUse.objects.create(
                    chat_message=chat_message,
                    use_type=ChatMessageTokenUse.UseTypeEnum.INPUT,
                    model_name=model,
                    token_count=token_count,
                )
        if metadata and metadata.output_tokens:
            for model, token_count in metadata.output_tokens.items():
                ChatMessageTokenUse.objects.create(
                    chat_message=chat_message,
                    use_type=ChatMessageTokenUse.UseTypeEnum.OUTPUT,
                    model_name=model,
                    token_count=token_count,
                )
        return chat_message

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
