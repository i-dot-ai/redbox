import json
import logging
from types import SimpleNamespace

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
from redbox_app.redbox_core.models import ChatHistory, ChatMessage, ChatRoleEnum, File, User
from websockets.client import connect
from yarl import URL

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    async def receive(self, text_data):
        data = json.loads(text_data)
        user_message_text = data.get("message", "")
        session_id = data.get("data-session-id", None)
        user: User = self.scope.get("user", None)

        session = await self.get_session(session_id, user, user_message_text)

        # save user message
        await self.save_message(session, user_message_text, ChatRoleEnum.user)

        # get LLM response
        session_messages = await self.get_messages(session)
        message_history: list[dict[str, str]] = [
            {"role": message.role, "text": message.text} for message in session_messages
        ]
        url = URL.build(scheme="ws", host=settings.CORE_API_HOST, port=settings.CORE_API_PORT) / "chat/rag-chat-stream"
        async with connect(str(url), extra_headers={"Authorization": user.get_bearer_token()}) as websocket:
            await websocket.send(json.dumps({"message_history": message_history}))
            await self.send(json.dumps({"type": "session-id", "data": session.id}))
            full_reply: list[str] = []
            sources: list[File] = []
            async for raw_message in websocket:
                message = json.loads(raw_message, object_hook=lambda d: SimpleNamespace(**d))
                logger.debug("Received: %s", message)
                if message.resource_type == "text":
                    await self.send(json.dumps({"type": "text", "data": message.data}))
                    full_reply.append(message.data)
                elif message.resource_type == "documents":
                    doc_uuids: list[str] = [doc.file_uuid for doc in message.data]
                    sources = File.objects.filter(core_file_uuid__in=doc_uuids, user=user)
                    for source in sources:
                        await self.send(
                            json.dumps(
                                {
                                    "type": "source",
                                    "data": {"url": source.url, "original_file_name": source.original_file_name},
                                }
                            )
                        )
                elif message.resource_type == "end":
                    await self.save_message(session, "".join(full_reply), ChatRoleEnum.ai, sources)

    @database_sync_to_async
    def get_session(self, session_id: str, user: User, user_message_text: str) -> ChatHistory:
        if session_id:
            session = ChatHistory.objects.get(id=session_id)
        else:
            session_name = user_message_text[0:20]
            session = ChatHistory(name=session_name, users=user)
            session.save()
        return session

    @database_sync_to_async
    def get_messages(self, session: ChatHistory) -> list[ChatMessage]:
        return list(ChatMessage.objects.filter(chat_history=session))

    @database_sync_to_async
    def save_message(
        self, session: ChatHistory, user_message_text: str, role: ChatRoleEnum, source_files: list[File] | None = None
    ) -> ChatMessage:
        chat_message = ChatMessage(
            chat_history=session, text=user_message_text, role=role, source_files=source_files or []
        )
        chat_message.save()
        return chat_message
