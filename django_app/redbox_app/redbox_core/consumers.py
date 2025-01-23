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
from langchain_core.documents import Document
from openai import RateLimitError
from websockets import ConnectionClosedError, WebSocketClientProtocol

from redbox import Redbox
from redbox.models.chain import (
    AISettings,
    ChainChatMessage,
    PromptSet,
    RedboxQuery,
    RedboxState,
)
from redbox_app.redbox_core import error_messages
from redbox_app.redbox_core.models import AISettings as AISettingsModel
from redbox_app.redbox_core.models import (
    Chat,
    ChatLLMBackend,
    ChatMessage,
    File,
)

User = get_user_model()
OptFileSeq = Sequence[File] | None
logger = logging.getLogger(__name__)
logger.info("WEBSOCKET_SCHEME is: %s", settings.WEBSOCKET_SCHEME)


def parse_page_number(obj: int | list[int] | None) -> list[int]:
    if isinstance(obj, int):
        return [obj]
    elif isinstance(obj, list) and len(obj) > 0 and all(isinstance(item, int) for item in obj):
        return obj
    elif obj is None:
        return []

    msg = "expected, int | list[int] | None got %s"
    raise ValueError(msg, type(obj))


def escape_curly_brackets(text: str):
    return text.replace("{", "{{").replace("}", "}}")


class ChatConsumer(AsyncWebsocketConsumer):
    full_reply: ClassVar = []
    route = None
    redbox = Redbox(debug=settings.DEBUG)

    async def receive(self, text_data=None, bytes_data=None):
        """Receive & respond to message from browser websocket."""
        self.full_reply = []
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

        # Update session name if this is the first message
        message_count = await session.chatmessage_set.acount()
        if message_count == 0:
            session.name = user_message_text[: settings.CHAT_TITLE_LENGTH]
            await session.asave()

        if await File.objects.filter(id__in=selected_file_uuids, status=File.Status.processing).aexists():
            await self.send_to_client("error", "you have files waiting to be processed")
            return

        # save user message
        selected_files = File.objects.filter(user=user, status=File.Status.complete, id__in=selected_file_uuids)
        await self.save_user_message(session, user_message_text, selected_files=selected_files)

        await self.llm_conversation(selected_files, session, user, user_message_text)
        await self.close()

    async def llm_conversation(self, selected_files: Sequence[File], session: Chat, user: User, title: str) -> None:
        """Initiate & close websocket conversation with the core-api message endpoint."""
        await self.send_to_client("session-id", session.id)

        session_messages = ChatMessage.objects.filter(chat=session).order_by("created_at")
        message_history: Sequence[Mapping[str, str]] = [message async for message in session_messages]

        ai_settings = await self.get_ai_settings(session)

        document_token_count = sum(file.token_count for file in selected_files if file.token_count)
        message_history_token_count = sum(message.token_count for message in message_history if message.token_count)

        if document_token_count + message_history_token_count > ai_settings.context_window_size:
            await self.send_to_client("error", "selected are too big to work with")
            return

        self.route = PromptSet.ChatwithDocs if selected_files else PromptSet.Chat
        self.send_to_client("route", self.route)

        state = RedboxState(
            request=RedboxQuery(
                question=message_history[-1].text,
                documents=[Document(str(f.text), metadata={"uri": f.original_file.name}) for f in selected_files],
                user_uuid=user.id,
                chat_history=[
                    ChainChatMessage(
                        role=message.role,
                        text=escape_curly_brackets(message.text),
                    )
                    for message in message_history[:-1]
                ],
                ai_settings=ai_settings,
            ),
        )

        try:
            await self.redbox.run(
                state,
                response_tokens_callback=self.handle_text,
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
        chat_message = ChatMessage(
            chat=session,
            text=user_message_text,
            role=ChatMessage.Role.user,
            route=self.route,
        )
        chat_message.save()
        if selected_files:
            chat_message.selected_files.set(selected_files)

        chat_message.log()

        return chat_message

    @database_sync_to_async
    def save_ai_message(
        self,
        session: Chat,
        user_message_text: str,
    ) -> ChatMessage:
        chat_message = ChatMessage(
            chat=session,
            text=user_message_text,
            role=ChatMessage.Role.ai,
            route=self.route,
        )
        chat_message.save()

        chat_message.log()

        return chat_message

    @staticmethod
    @database_sync_to_async
    def get_ai_settings(chat: Chat) -> AISettings:
        ai_settings = model_to_dict(chat.user.ai_settings, exclude=["label", "chat_backend"])
        ai_settings["chat_backend"] = model_to_dict(chat.chat_backend)

        # we remove null values so that AISettings can populate them with defaults
        ai_settings = {k: v for k, v in ai_settings.items() if v not in (None, "")}
        return AISettings.model_validate(ai_settings)

    async def handle_text(self, response: str) -> str:
        await self.send_to_client("text", response)
        self.full_reply.append(response)
