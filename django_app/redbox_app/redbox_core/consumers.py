import asyncio
import json
import logging
from collections.abc import Mapping
from typing import Any

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
from django.contrib.auth import get_user_model
from openai import RateLimitError

from redbox import run_async
from redbox_app.redbox_core import error_messages
from redbox_app.redbox_core.models import (
    ChatMessage,
    get_chat_session,
)

User = get_user_model()
logger = logging.getLogger(__name__)
logger.info("WEBSOCKET_SCHEME is: %s", settings.WEBSOCKET_SCHEME)


class ChatConsumer(AsyncWebsocketConsumer):
    async def receive(self, text_data=None, _bytes_data=None):
        """Receive & respond to message from browser websocket."""

        data = json.loads(text_data)
        logger.debug("received %s from browser", data)

        try:
            user: User = self.scope["user"]
            chat_id = self.scope["url_route"]["kwargs"]["chat_id"]
        except KeyError:
            await self.close()
            await self.send_to_client("error", error_messages.CORE_ERROR_MESSAGE)
            raise

        try:
            chat, delay = await sync_to_async(get_chat_session)(chat_id=chat_id, user=user, data=data)
        except ValueError as e:
            await self.send_to_client("error", e.args[0])
            await self.close()
            return

        if delay > settings.MESSAGE_THROTTLE_SECONDS_MIN:
            await self.send_to_client("info", "Due to high demand your message is being queued")
            if delay > settings.MESSAGE_THROTTLE_SECONDS_MAX:
                logger.error("delay=%s > %s, this will be capped", delay, settings.MESSAGE_THROTTLE_SECONDS_MAX)
            await asyncio.sleep(max(delay, settings.MESSAGE_THROTTLE_SECONDS_MAX))

        await self.send_to_client("info", "Loading")

        state = await sync_to_async(chat.to_langchain)()

        try:
            state = await run_async(
                state,
                response_tokens_callback=self.handle_text,
            )

            message = await ChatMessage.objects.acreate(
                chat=chat,
                text=state.content,
                role=ChatMessage.Role.ai,
                delay=delay,
            )

            await self.send_to_client("end", {"message_id": message.id, "title": chat.name, "session_id": chat.id})

        except RateLimitError as e:
            logger.exception("Rate limit error", exc_info=e)
            await self.send_to_client("error", error_messages.RATE_LIMITED)

        except BaseException as e:
            logger.exception("General error.", exc_info=e)
            await self.send_to_client("error", error_messages.CORE_ERROR_MESSAGE)

        await self.close()

    async def send_to_client(self, message_type: str, data: str | Mapping[str, Any] | None = None) -> None:
        message = {"type": message_type, "data": data}
        await self.send(json.dumps(message, default=str))

    async def handle_text(self, response: str):
        await self.send_to_client("text", response)
