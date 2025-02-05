import json
import logging
from asyncio import CancelledError
from collections.abc import Mapping, Sequence
from typing import Any

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
from redbox_app.redbox_core.utils import sanitise_string

User = get_user_model()
OptFileSeq = Sequence[File] | None
logger = logging.getLogger(__name__)
logger.info("WEBSOCKET_SCHEME is: %s", settings.WEBSOCKET_SCHEME)


async def get_unique_chat_title(title: str, user: User, number: int = 0) -> str:
    original_title = sanitise_string(title[: settings.CHAT_TITLE_LENGTH])
    new_title = original_title
    if number > 0:
        new_title = f"{original_title} ({number})"
    if await Chat.objects.filter(name=new_title, user=user).aexists():
        return await get_unique_chat_title(original_title, user, number + 1)
    return new_title


class ChatConsumer(AsyncWebsocketConsumer):
    redbox = Redbox(debug=settings.DEBUG)

    async def receive(self, text_data=None, _bytes_data=None):
        """Receive & respond to message from browser websocket."""

        data = json.loads(text_data)
        logger.debug("received %s from browser", data)
        user_message_text: str = data.get("message", "")
        try:
            user: User = self.scope["user"]
            chat_id = self.scope["url_route"]["kwargs"]["chat_id"]
        except KeyError:
            await self.close()
            await self.send_to_client("error", error_messages.CORE_ERROR_MESSAGE)
            raise

        chat = await Chat.objects.aget(id=chat_id)

        if chat_backend_id := data.get("llm"):
            chat.chat_backend = await ChatLLMBackend.objects.aget(id=chat_backend_id)
            await chat.asave()

        if temperature := data.get("temperature", 0):
            chat.temperature = temperature
            await chat.asave()

        # Update session name if this is the first message
        if await chat.chatmessage_set.acount() == 0:
            chat.name = await get_unique_chat_title(user_message_text, user)
            await chat.asave()

        token_count = await sync_to_async(chat.token_count)()

        active_context_window_sizes = await sync_to_async(ChatLLMBackend.active_context_window_sizes)()

        if token_count > max(active_context_window_sizes.values()):
            await self.send_to_client("error", error_messages.FILES_TOO_LARGE)
            await self.close()
            return

        if token_count > await sync_to_async(chat.context_window_size)():
            details = "\n".join(
                f"* `{k}`: {v} tokens" for k, v in active_context_window_sizes.items() if v >= token_count
            )
            msg = f"{error_messages.FILES_TOO_LARGE}.\nTry one of the following models:\n{details}"
            await self.send_to_client("error", msg)
            await self.close()
            return

        # save user message
        await self.save_message(chat, user_message_text, ChatMessage.Role.user)
        await self.llm_conversation(chat)
        await self.close()

    async def llm_conversation(self, session: Chat) -> None:
        """Initiate & close websocket conversation with the core-api message endpoint."""

        state = await sync_to_async(session.to_langchain)()

        try:
            state = await self.redbox.run(
                state,
                response_tokens_callback=self.handle_text,
            )

            message = await self.save_message(session, state.messages[-1], ChatMessage.Role.ai)
            await self.send_to_client(
                "end", {"message_id": message.id, "title": session.name, "session_id": session.id}
            )

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
        )
        chat_message.save()
        return chat_message

    async def handle_text(self, response: str) -> str:
        await self.send_to_client("text", response)
