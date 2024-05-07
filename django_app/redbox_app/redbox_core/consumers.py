import json
import logging
from time import sleep

from channels.generic.websocket import WebsocketConsumer
from django.conf import settings
from redbox_app.redbox_core.client import CoreApiClient
from redbox_app.redbox_core.models import ChatHistory, ChatMessage, ChatRoleEnum

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class ChatConsumer(WebsocketConsumer):
    def receive(self, text_data):
        data = json.loads(text_data)
        user = self.scope.get("user", None)
        logger.debug(f"receive {text_data=} {user=}")
        user_message_text = data.get("message", "")

        if session_id := data.get("sessionId", None):
            session = ChatHistory.objects.get(id=session_id)
        else:
            session_name = user_message_text[0:20]
            session = ChatHistory(name=session_name, users=user)
            session.save()

        # save user message
        chat_message = ChatMessage(chat_history=session, text=user_message_text, role=ChatRoleEnum.user)
        chat_message.save()

        # get LLM response
        message_history = [
            {"role": message.role, "text": message.text} for message in ChatMessage.objects.filter(chat_history=session)
        ]
        core_api = CoreApiClient(host=settings.CORE_API_HOST, port=settings.CORE_API_PORT)
        ai_message_text = core_api.rag_chat(message_history, user.get_bearer_token())

        # save LLM response
        llm_message = ChatMessage(chat_history=session, text=ai_message_text, role=ChatRoleEnum.ai)
        llm_message.save()

        self.send(ai_message_text)
        sleep(0.5)
        self.send(" MESSAGE END")
