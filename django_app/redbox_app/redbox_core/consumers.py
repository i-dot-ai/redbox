import json
import logging
from asyncio import CancelledError
from collections.abc import Mapping, Sequence
from typing import Any, ClassVar
from uuid import UUID

from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
from django.contrib.auth import get_user_model
from openai import RateLimitError
from websockets import ConnectionClosedError

from redbox import Redbox
from redbox_app.redbox_core import error_messages
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

        if chat_backend_id := data.get("llm"):
            chat_backend = await ChatLLMBackend.objects.aget(id=chat_backend_id)
        else:
            chat_backend = await ChatLLMBackend.objects.aget(is_default=True)

        temperature = data.get("temperature", 0)

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
        await self.save_message(session, user_message_text, ChatMessage.Role.user)
        await self.llm_conversation(session, user_message_text)
        await self.close()

    async def llm_conversation(self, session: Chat, title: str) -> None:
        """Initiate & close websocket conversation with the core-api message endpoint."""
        await self.send_to_client("session-id", session.id)

        token_count = await sync_to_async(session.token_count)()

        if token_count > session.chat_backend.context_window_size:
            await self.send_to_client("error", "selected are too big to work with")
            return

        self.route = "chat_with_docs"  # if selected_files else "chat"
        self.send_to_client("route", self.route)

        state = await sync_to_async(session.to_langchain)()

        try:
            await self.redbox.run(
                state,
                response_tokens_callback=self.handle_text,
            )

            message = await self.save_message(session, "".join(self.full_reply), ChatMessage.Role.ai)
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

    @database_sync_to_async
    def save_message(self, session: Chat, user_message_text: str, role: ChatMessage.Role) -> ChatMessage:
        chat_message = ChatMessage(
            chat=session,
            text=user_message_text,
            role=role,
            route=self.route,
        )
        chat_message.save()

        chat_message.log()

        return chat_message

    async def handle_text(self, response: str) -> str:
        await self.send_to_client("text", response)
        self.full_reply.append(response)
