import json
import logging
from collections.abc import Mapping, MutableSequence, Sequence
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from dataclasses_json import Undefined, dataclass_json
from django.conf import settings
from django.utils import timezone
from redbox_app.redbox_core.models import ChatHistory, ChatMessage, ChatRoleEnum, File, User
from websockets import WebSocketClientProtocol
from websockets.client import connect
from yarl import URL

OptFileSeq = Sequence[File] | None
logger = logging.getLogger(__name__)
logger.info("WEBSOCKET_SCHEME is: %s", settings.WEBSOCKET_SCHEME)


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass(frozen=True)
class CoreChatResponseDoc:
    file_uuid: str


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass(frozen=True)
class CoreChatResponse:
    resource_type: Literal["text", "documents", "end"]
    data: list[CoreChatResponseDoc] | str | None = None


class ChatConsumer(AsyncWebsocketConsumer):
    async def receive(self, text_data=None, bytes_data=None):
        data = json.loads(text_data or bytes_data)
        logger.debug("received %s from browser", data)
        user_message_text: str = data.get("message", "")
        session_id: str | None = data.get("sessionId", None)
        selected_file_uuids: Sequence[UUID] = [UUID(u) for u in data.get("selectedFiles", [])]
        user: User = self.scope.get("user", None)

        session: ChatHistory = await self.get_session(session_id, user, user_message_text)

        # save user message
        selected_files = await self.get_files_by_id(selected_file_uuids, user)
        await self.save_message(session, user_message_text, ChatRoleEnum.user, selected_files=selected_files)

        await self.llm_conversation(selected_files, session, user)
        await self.close()

    async def llm_conversation(self, selected_files: Sequence[File], session: ChatHistory, user: User) -> None:
        session_messages = await self.get_messages(session)
        message_history: Sequence[Mapping[str, str]] = [
            {"role": message.role, "text": message.text} for message in session_messages
        ]
        url = URL.build(scheme="ws", host=settings.CORE_API_HOST, port=settings.CORE_API_PORT) / "chat/rag"
        async with connect(str(url), extra_headers={"Authorization": user.get_bearer_token()}) as core_websocket:
            message = {
                "message_history": message_history,
                "selected_files": [{"uuid": f.core_file_uuid} for f in selected_files],
            }
            await self.send_to_server(core_websocket, message)
            await self.send_to_client({"type": "session-id", "data": str(session.id)})
            reply, source_files = await self.receive_llm_responses(user, core_websocket)
        await self.save_message(session, reply, ChatRoleEnum.ai, source_files=source_files)

        for file in source_files:
            file.last_referenced = timezone.now()
            await self.file_save(file)

    async def receive_llm_responses(
        self, user: User, core_websocket: WebSocketClientProtocol
    ) -> tuple[str, Sequence[File]]:
        full_reply: MutableSequence[str] = []
        source_files: MutableSequence[File] = []
        async for raw_message in core_websocket:
            message = CoreChatResponse.schema().loads(raw_message)
            logger.debug("received %s from core-api", message)
            if message.resource_type == "text":
                full_reply.append(await self.handle_text(message))
            elif message.resource_type == "documents":
                source_files += await self.handle_documents(message, user)
        return "".join(full_reply), source_files

    async def handle_documents(self, message: CoreChatResponse, user: User) -> Sequence[File]:
        doc_uuids: Sequence[UUID] = [UUID(doc.file_uuid) for doc in message.data]
        source_files = await self.get_files_by_core_uuid(doc_uuids, user)
        for source in source_files:
            await self.send_to_client(
                {
                    "type": "source",
                    "data": {"url": str(source.url), "original_file_name": source.original_file_name},
                }
            )
        return source_files

    async def handle_text(self, message: CoreChatResponse) -> str:
        await self.send_to_client({"type": "text", "data": message.data})
        return message.data

    async def send_to_client(self, data):
        logger.debug("sending %s to browser", data)
        await self.send(json.dumps(data, default=str))

    @staticmethod
    async def send_to_server(websocket, data):
        logger.debug("sending %s to core-api", data)
        return await websocket.send(json.dumps(data, default=str))

    @staticmethod
    @database_sync_to_async
    def get_session(session_id: str, user: User, user_message_text: str) -> ChatHistory:
        if session_id:
            session = ChatHistory.objects.get(id=session_id)
        else:
            session_name = user_message_text[0 : settings.CHAT_TITLE_LENGTH]
            session = ChatHistory(name=session_name, users=user)
            session.save()
        return session

    @staticmethod
    @database_sync_to_async
    def get_messages(session: ChatHistory) -> Sequence[ChatMessage]:
        return list(ChatMessage.objects.filter(chat_history=session).order_by("created_at"))

    @staticmethod
    @database_sync_to_async
    def save_message(
        session: ChatHistory,
        user_message_text: str,
        role: ChatRoleEnum,
        source_files: OptFileSeq = None,
        selected_files: OptFileSeq = None,
    ) -> ChatMessage:
        chat_message = ChatMessage(chat_history=session, text=user_message_text, role=role)
        chat_message.save()
        if source_files:
            chat_message.source_files.set(source_files)
        if selected_files:
            chat_message.selected_files.set(selected_files)
        return chat_message

    @staticmethod
    @database_sync_to_async
    def get_files_by_id(uuids: Sequence[UUID], user: User) -> Sequence[File]:
        return list(File.objects.filter(id__in=uuids, user=user))

    @staticmethod
    @database_sync_to_async
    def get_files_by_core_uuid(uuids: Sequence[UUID], user: User) -> Sequence[File]:
        return list(File.objects.filter(core_file_uuid__in=uuids, user=user))

    @staticmethod
    @database_sync_to_async
    def file_save(file):
        return file.save()
