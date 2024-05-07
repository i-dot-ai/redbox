import json
import logging
from time import sleep

from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
from redbox_app.redbox_core.client import CoreApiClient
from redbox_app.redbox_core.models import ChatHistory, ChatMessage, ChatRoleEnum, User
from channels.db import database_sync_to_async


logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class ChatConsumer(AsyncWebsocketConsumer):
    async def receive(self, text_data):
        data = json.loads(text_data)
        user_message_text = data.get("message", "")
        session_id = data.get("sessionId", None)
        user: User = self.scope.get("user", None)
        logger.debug(f"receive {user_message_text=} {session_id=} {user=}")

        session = await self.get_session(session_id, user, user_message_text)

        # save user message
        await self.save_message(session, user_message_text, ChatRoleEnum.user)

        # get LLM response
        session_messages = await self.get_messages(session)
        message_history = [{"role": message.role, "text": message.text} for message in session_messages]
        core_api = CoreApiClient(host=settings.CORE_API_HOST, port=settings.CORE_API_PORT)
        ai_message_text = core_api.rag_chat(message_history, user.get_bearer_token())

        # save LLM response
        await self.save_message(session, ai_message_text, ChatRoleEnum.ai)

        await self.send(ai_message_text)
        sleep(0.5)
        await self.send(" MESSAGE END")

    @database_sync_to_async
    def get_session(self, session_id: str, user: User, user_message_text: str):
        if session_id:
            session = ChatHistory.objects.get(id=session_id)
        else:
            session_name = user_message_text[0:20]
            session = ChatHistory(name=session_name, users=user)
            session.save()
        return session

    @database_sync_to_async
    def get_messages(self, session):
        return list(ChatMessage.objects.filter(chat_history=session))

    @database_sync_to_async
    def save_message(self, session, user_message_text, role):
        chat_message = ChatMessage(chat_history=session, text=user_message_text, role=role)
        chat_message.save()
