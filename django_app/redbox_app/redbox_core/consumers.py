import json
import logging
from asyncio import CancelledError
from collections.abc import Mapping, Sequence
from typing import Any, ClassVar
from uuid import UUID

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
from django.contrib.auth import get_user_model
from django.forms.models import model_to_dict
from django.utils import timezone
from langchain_core.documents import Document
from openai import RateLimitError
from websockets import ConnectionClosedError, WebSocketClientProtocol

from redbox import Redbox
from redbox.models import Settings
from redbox.models.chain import (
    AISettings,
    ChainChatMessage,
    RedboxQuery,
    RedboxState,
    RequestMetadata,
    metadata_reducer,
)
from redbox.models.graph import RedboxActivityEvent
from redbox_app.redbox_core import error_messages
from redbox_app.redbox_core.models import (
    ActivityEvent,
    Chat,
    ChatLLMBackend,
    ChatMessage,
    ChatMessageTokenUse,
    ChatRoleEnum,
    Citation,
    ExternalCitation,
    File,
    StatusEnum,
)
from redbox_app.redbox_core.models import (
    AISettings as AISettingsModel,
)

User = get_user_model()
OptFileSeq = Sequence[File] | None
logger = logging.getLogger(__name__)
logger.info("WEBSOCKET_SCHEME is: %s", settings.WEBSOCKET_SCHEME)


def parse_page_number(obj: int | list[int] | None) -> list[int]:
    if isinstance(obj, int):
        return [obj]
    if isinstance(obj, list) and all(isinstance(item, int) for item in obj):
        return obj
    if obj is None:
        return []

    msg = "expected, int | list[int] | None got %s"
    raise ValueError(msg, type(obj))


def escape_curly_brackets(text: str):
    return text.replace("{", "{{").replace("}", "}}")


class ChatConsumer(AsyncWebsocketConsumer):
    full_reply: ClassVar = []
    citations: ClassVar = []
    external_citations: ClassVar = []
    activities: ClassVar = []
    route = None
    metadata: RequestMetadata = RequestMetadata()
    redbox = Redbox(env=Settings(), debug=True)

    async def receive(self, text_data=None, bytes_data=None):
        """Receive & respond to message from browser websocket."""
        self.full_reply = []
        self.citations = []
        self.external_citations = []
        self.route = None

        data = json.loads(text_data or bytes_data)
        logger.debug("received %s from browser", data)
        user_message_text: str = data.get("message", "")
        selected_file_uuids: Sequence[UUID] = [UUID(u) for u in data.get("selectedFiles", [])]
        user: User = self.scope.get("user")

        user_ai_settings = await AISettingsModel.objects.aget(label=user.ai_settings_id)

        chat_backend = await ChatLLMBackend.objects.aget(id=data.get("llm", user_ai_settings.chat_backend_id))
        temperature = data.get("temperature", user_ai_settings.temperature)

        if session_id := data.get("sessionId"):
            session = await Chat.objects.aget(id=session_id)
            session.chat_backend = chat_backend
            session.temperature = temperature
            logger.info("updating session: chat_backend=%s temperature=%s", chat_backend, temperature)
            await session.asave()
        else:
            logger.info("creating session: chat_backend=%s temperature=%s", chat_backend, temperature)
            session = await Chat.objects.acreate(
                name=user_message_text[: settings.CHAT_TITLE_LENGTH],
                user=user,
                chat_backend=chat_backend,
                temperature=temperature,
            )

        # save user message
        permitted_files = File.objects.filter(user=user, status=StatusEnum.complete)
        selected_files = permitted_files.filter(id__in=selected_file_uuids)
        await self.save_user_message(session, user_message_text, selected_files=selected_files)

        await self.llm_conversation(selected_files, session, user, user_message_text, permitted_files)
        await self.close()

    async def llm_conversation(
        self, selected_files: Sequence[File], session: Chat, user: User, title: str, permitted_files: Sequence[File]
    ) -> None:
        """Initiate & close websocket conversation with the core-api message endpoint."""
        await self.send_to_client("session-id", session.id)

        session_messages = ChatMessage.objects.filter(chat=session).order_by("created_at")
        message_history: Sequence[Mapping[str, str]] = [message async for message in session_messages]

        ai_settings = await self.get_ai_settings(session)
        state = RedboxState(
            request=RedboxQuery(
                question=message_history[-1].text,
                s3_keys=[f.unique_name for f in selected_files],
                user_uuid=user.id,
                chat_history=[
                    ChainChatMessage(
                        role=message.role,
                        text=escape_curly_brackets(message.text),
                    )
                    for message in message_history[:-1]
                ],
                ai_settings=ai_settings,
                permitted_s3_keys=[f.unique_name async for f in permitted_files],
            ),
        )

        try:
            await self.redbox.run(
                state,
                response_tokens_callback=self.handle_text,
                route_name_callback=self.handle_route,
                documents_callback=self.handle_documents,
                metadata_tokens_callback=self.handle_metadata,
                activity_event_callback=self.handle_activity,
            )

            message = await self.save_ai_message(
                session,
                "".join(self.full_reply),
            )
            await self.send_to_client("end", {"message_id": message.id, "title": title, "session_id": session.id})

        except RateLimitError as e:
            logger.exception("Rate limit error", exc_info=e)
            await self.send_to_client("error", error_messages.RATE_LIMITED)
        except (TimeoutError, ConnectionClosedError, CancelledError) as e:
            logger.exception("Error from core.", exc_info=e)
            await self.send_to_client("error", error_messages.CORE_ERROR_MESSAGE)
        except Exception as e:
            logger.exception("General error.", exc_info=e)
            await self.send_to_client("error", error_messages.CORE_ERROR_MESSAGE)

    async def send_to_client(self, message_type: str, data: str | Mapping[str, Any] | None = None) -> None:
        message = {"type": message_type, "data": data}
        logger.debug("sending %s to browser", message)
        await self.send(json.dumps(message, default=str))

    @staticmethod
    async def send_to_server(websocket: WebSocketClientProtocol, data: Mapping[str, Any]) -> None:
        logger.debug("sending %s to core-api", data)
        return await websocket.send(json.dumps(data, default=str))

    @database_sync_to_async
    def save_user_message(
        self,
        session: Chat,
        user_message_text: str,
        selected_files: Sequence[File] | None = None,
    ) -> ChatMessage:
        chat_message = ChatMessage(chat=session, text=user_message_text, role=ChatRoleEnum.user, route=self.route)
        chat_message.save()
        if selected_files:
            chat_message.selected_files.set(selected_files)
        return chat_message

    @database_sync_to_async
    def save_ai_message(
        self,
        session: Chat,
        user_message_text: str,
    ) -> ChatMessage:
        chat_message = ChatMessage(chat=session, text=user_message_text, role=ChatRoleEnum.ai, route=self.route)
        chat_message.save()
        for file, citations in self.citations:
            file.last_referenced = timezone.now()
            file.save()

            for citation in citations:
                Citation.objects.create(
                    chat_message=chat_message,
                    file=file,
                    text=citation.page_content,
                    page_numbers=parse_page_number(citation.metadata.get("page_number")),
                )

        for document in self.external_citations:
            ExternalCitation.objects.create(
                chat_message=chat_message,
                text=document.page_content,
                creator=document.metadata.get("creator_type", "Unknown"),
                url=document.metadata.get("original_resource_ref", "Unknown"),
            )

        if self.metadata and self.metadata.input_tokens:
            for model, token_count in self.metadata.input_tokens.items():
                ChatMessageTokenUse.objects.create(
                    chat_message=chat_message,
                    use_type=ChatMessageTokenUse.UseTypeEnum.INPUT,
                    model_name=model,
                    token_count=token_count,
                )

        if self.metadata and self.metadata.output_tokens:
            for model, token_count in self.metadata.output_tokens.items():
                ChatMessageTokenUse.objects.create(
                    chat_message=chat_message,
                    use_type=ChatMessageTokenUse.UseTypeEnum.OUTPUT,
                    model_name=model,
                    token_count=token_count,
                )

        if self.activities:
            for activity in self.activities:
                ActivityEvent.objects.create(chat_message=chat_message, message=activity.message)

        return chat_message

    @staticmethod
    @database_sync_to_async
    def get_ai_settings(chat: Chat) -> AISettings:
        ai_settings = model_to_dict(chat.user.ai_settings, exclude=["label", "chat_backend"])
        ai_settings["chat_backend"] = model_to_dict(chat.chat_backend)
        return AISettings.model_validate(ai_settings)

    async def handle_text(self, response: str) -> str:
        await self.send_to_client("text", response)
        self.full_reply.append(response)

    async def handle_route(self, response: str) -> str:
        await self.send_to_client("route", response)
        self.route = response

    async def handle_metadata(self, response: dict):
        self.metadata = metadata_reducer(self.metadata, RequestMetadata.model_validate(response))

    async def handle_activity(self, response: dict):
        self.activities.append(RedboxActivityEvent.model_validate(response))

    async def handle_documents(self, response: list[Document]):
        sources = {doc.metadata["original_resource_ref"] for doc in response}
        files = File.objects.filter(original_file__in=sources)
        handled_sources = set()
        async for file in files:
            await self.send_to_client("source", {"url": str(file.url), "original_file_name": file.original_file_name})
            self.citations.append(
                (file, [doc for doc in response if doc.metadata["original_resource_ref"] == file.unique_name])
            )
            handled_sources.add(file.original_file_name)

        additional_sources = [doc for doc in response if doc.metadata["original_resource_ref"] not in handled_sources]

        for additional_source in additional_sources:
            url = additional_source.metadata["original_resource_ref"]
            source = additional_source.metadata.get("creator_type", "Unknown")
            await self.send_to_client("source", {"url": url, "original_file_name": f"{source} - {url.split("/")[-1]}"})
            self.external_citations.append(
                (file, [doc for doc in response if doc.metadata["original_resource_ref"] == file.unique_name])
            )

    async def handle_activity_event(self, event: RedboxActivityEvent):
        logger.info("ACTIVITY: %s", event.message)
