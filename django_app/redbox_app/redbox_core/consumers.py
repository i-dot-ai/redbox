import json
import logging
from asyncio import CancelledError
from collections import defaultdict
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
from redbox.models.chain import (
    AISettings,
    ChainChatMessage,
    RedboxQuery,
    RedboxState,
    RequestMetadata,
    Source,
    metadata_reducer,
)
from redbox.models.chain import Citation as AICitation
from redbox.models.graph import RedboxActivityEvent
from redbox.models.settings import get_settings
from redbox_app.redbox_core import error_messages
from redbox_app.redbox_core.models import (
    ActivityEvent,
    Chat,
    ChatLLMBackend,
    ChatMessage,
    ChatMessageTokenUse,
    Citation,
    File,
)
from redbox_app.redbox_core.models import AISettings as AISettingsModel

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
    citations: ClassVar[list[tuple[File, AICitation]]] = []
    activities: ClassVar[list[RedboxActivityEvent]] = []
    route = None
    metadata: RequestMetadata = RequestMetadata()
    redbox = Redbox(env=get_settings(), debug=True)

    async def receive(self, text_data=None, bytes_data=None):
        """Receive & respond to message from browser websocket."""
        self.full_reply = []
        self.citations = []
        self.external_citations = []
        self.route = None
        self.activities = []

        data = json.loads(text_data or bytes_data)
        logger.debug("received %s from browser", data)
        user_message_text: str = data.get("message", "")
        selected_file_uuids: Sequence[UUID] = [UUID(u) for u in data.get("selectedFiles", [])]
        activities: Sequence[str] = data.get("activities", [])
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
        permitted_files = File.objects.filter(user=user, status=File.Status.complete)
        selected_files = permitted_files.filter(id__in=selected_file_uuids)
        await self.save_user_message(session, user_message_text, selected_files=selected_files, activities=activities)

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
                citations_callback=self.handle_citations,
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
        activities: Sequence[str] | None = None,
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

        # Save user activities
        for message in activities:
            activity = ActivityEvent.objects.create(chat_message=chat_message, message=message)
            activity.save()

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
        for file, ai_citation in self.citations:
            for citation_source in ai_citation.sources:
                if file:
                    file.last_referenced = timezone.now()
                    file.save()
                    Citation.objects.create(
                        chat_message=chat_message,
                        text_in_answer=ai_citation.text_in_answer,
                        file=file,
                        text=citation_source.highlighted_text_in_source,
                        page_numbers=citation_source.page_numbers,
                        source=Citation.Origin.USER_UPLOADED_DOCUMENT,
                    )
                else:
                    Citation.objects.create(
                        chat_message=chat_message,
                        text_in_answer=ai_citation.text_in_answer,
                        url=citation_source.source,
                        text=citation_source.highlighted_text_in_source,
                        page_numbers=citation_source.page_numbers,
                        source=Citation.Origin.try_parse(citation_source.source_type),
                    )

        if self.metadata:
            for model, token_count in self.metadata.input_tokens.items():
                ChatMessageTokenUse.objects.create(
                    chat_message=chat_message,
                    use_type=ChatMessageTokenUse.UseType.INPUT,
                    model_name=model,
                    token_count=token_count,
                )
            for model, token_count in self.metadata.output_tokens.items():
                ChatMessageTokenUse.objects.create(
                    chat_message=chat_message,
                    use_type=ChatMessageTokenUse.UseType.OUTPUT,
                    model_name=model,
                    token_count=token_count,
                )

        if self.activities:
            for activity in self.activities:
                ActivityEvent.objects.create(chat_message=chat_message, message=activity.message)

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

    async def handle_route(self, response: str) -> str:
        await self.send_to_client("route", response)
        self.route = response

    async def handle_metadata(self, response: dict):
        self.metadata = metadata_reducer(self.metadata, RequestMetadata.model_validate(response))

    async def handle_activity(self, response: dict):
        await self.send_to_client("activity", response.message)
        self.activities.append(RedboxActivityEvent.model_validate(response))

    async def handle_documents(self, response: list[Document]):
        """
        Map documents used to create answer to AICitations for storing as citations
        """
        sources_by_resource_ref: dict[str, Document] = defaultdict(list)
        for document in response:
            ref = document.metadata.get("uri")
            sources_by_resource_ref[ref].append(document)

        for ref, sources in sources_by_resource_ref.items():
            try:
                file = await File.objects.aget(original_file=ref)
                payload = {"url": str(file.url), "file_name": file.file_name}
                response_sources = [
                    Source(
                        source=str(file.url),
                        source_type=Citation.Origin.USER_UPLOADED_DOCUMENT,
                        document_name=file.file_name,
                        highlighted_text_in_source=cited_chunk.page_content,
                        page_numbers=parse_page_number(cited_chunk.metadata.get("page_number")),
                    )
                    for cited_chunk in sources
                ]
            except File.DoesNotExist:
                file = None
                payload = {"url": ref, "file_name": None}
                response_sources = [
                    Source(
                        source=cited_chunk.metadata["uri"],
                        source_type=cited_chunk.metadata["creator_type"],
                        document_name=cited_chunk.metadata["uri"].split("/")[-1],
                        highlighted_text_in_source=cited_chunk.page_content,
                        page_numbers=parse_page_number(cited_chunk.metadata.get("page_number")),
                    )
                    for cited_chunk in sources
                ]

            await self.send_to_client("source", payload)
            self.citations.append((file, AICitation(text_in_answer="", sources=response_sources)))

    async def handle_citations(self, citations: list[AICitation]):
        """
        Map AICitations used to create answer to AICitations for storing as citations. The link to user files
        must be populated
        """
        for c in citations:
            for s in c.sources:
                try:
                    file = await File.objects.aget(original_file=s.source)
                    payload = {"url": str(file.url), "file_name": file.file_name, "text_in_answer": c.text_in_answer}
                except File.DoesNotExist:
                    file = None
                    payload = {"url": s.source, "file_name": s.source, "text_in_answer": c.text_in_answer}
                await self.send_to_client("source", payload)
                self.citations.append((file, AICitation(text_in_answer=c.text_in_answer, sources=[s])))

    async def handle_activity_event(self, event: RedboxActivityEvent):
        logger.info("ACTIVITY: %s", event.message)
