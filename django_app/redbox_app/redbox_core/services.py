from collections.abc import Mapping, Sequence
from typing import ClassVar

from django.forms.models import model_to_dict
from django.utils import timezone
from langchain_core.documents import Document

from redbox import Redbox
from redbox.models import Settings
from redbox.models.chain import ChainChatMessage, RedboxQuery, RedboxState
from redbox.models.chat import MetadataDetail
from redbox_app.redbox_core.models import (
    AISettings,
    Chat,
    ChatMessage,
    ChatMessageTokenUse,
    ChatRoleEnum,
    Citation,
    File,
    User,
)
from redbox_app.redbox_core.utils import parse_page_number


def retrieve_llm_response(selected_files: Sequence[File], session: Chat, user: User):
    # TODO: fixme - currently the task runs 'successfully', but chats aren't being saved
    # coroutine 'RedboxDjangoInterface.post_llm_request' was never awaited
    interface = RedboxDjangoInterface()

    interface.post_llm_request(selected_files, session, user)


class RedboxDjangoInterface:
    # TODO: see if you can move some of ChatConsumer here to be DRY
    full_reply: ClassVar = []
    citations: ClassVar = []
    route = None
    metadata: MetadataDetail = MetadataDetail()
    redbox = Redbox(env=Settings(), debug=True)

    async def post_llm_request(self, selected_files: Sequence[File], session: Chat, user: User):
        session_messages = ChatMessage.objects.filter(chat=session).order_by("created_at")
        message_history: Sequence[Mapping[str, str]] = [message async for message in session_messages]

        ai_settings = await self.get_ai_settings(session)

        state = RedboxState(
            request=RedboxQuery(
                question=message_history[-1].text,
                s3_keys=[f.unique_name for f in selected_files],
                user_uuid=user.id,
                chat_history=[
                    ChainChatMessage(role=message.role, text=message.text) for message in message_history[:-1]
                ],
                ai_settings=ai_settings,
            ),
        )

        await self.redbox.run(
            state,
            response_tokens_callback=self.handle_text,
            route_name_callback=self.handle_route,
            documents_callback=self.handle_documents,
            metadata_tokens_callback=self.handle_metadata,
        )

        await self.save_message(
            session,
            "".join(self.full_reply),
            ChatRoleEnum.ai,
        )

        session.awaiting_llm_response = False
        session.save()

    @staticmethod
    def get_ai_settings(chat: Chat) -> AISettings:
        ai_settings = model_to_dict(chat.user.ai_settings, exclude=["label"])

        match str(chat.chat_backend):
            case "claude-3-sonnet":
                chat_backend = "anthropic.claude-3-sonnet-20240229-v1:0"
            case "claude-3-haiku":
                chat_backend = "anthropic.claude-3-haiku-20240307-v1:0"
            case _:
                chat_backend = str(chat.chat_backend)

        ai_settings["chat_backend"] = chat_backend
        return AISettings.parse_obj(ai_settings)

    @staticmethod
    def save_message(
        session: Chat,
        user_message_text: str,
        role: ChatRoleEnum,
        sources: Sequence[tuple[File, Document]] | None = None,
        selected_files: Sequence[File] | None = None,
        metadata: MetadataDetail | None = None,
        route: str | None = None,
    ) -> ChatMessage:
        chat_message = ChatMessage(chat=session, text=user_message_text, role=role, route=route)
        chat_message.save()
        if sources:
            for file, citations in sources:
                file.last_referenced = timezone.now()
                file.save()

                for citation in citations:
                    Citation.objects.create(
                        chat_message=chat_message,
                        file=file,
                        text=citation.page_content,
                        page_numbers=parse_page_number(citation.metadata.get("page_number")),
                    )
        if selected_files:
            chat_message.selected_files.set(selected_files)

        if metadata and metadata.input_tokens:
            for model, token_count in metadata.input_tokens.items():
                ChatMessageTokenUse.objects.create(
                    chat_message=chat_message,
                    use_type=ChatMessageTokenUse.UseTypeEnum.INPUT,
                    model_name=model,
                    token_count=token_count,
                )
        if metadata and metadata.output_tokens:
            for model, token_count in metadata.output_tokens.items():
                ChatMessageTokenUse.objects.create(
                    chat_message=chat_message,
                    use_type=ChatMessageTokenUse.UseTypeEnum.OUTPUT,
                    model_name=model,
                    token_count=token_count,
                )
        return chat_message

    def handle_text(self, response: str) -> None:
        self.full_reply.append(response)

    def handle_route(self, response: str) -> None:
        self.route = response

    def handle_metadata(self, response: dict):
        metadata_detail = MetadataDetail.parse_obj(response)
        for model, token_count in metadata_detail.input_tokens.items():
            self.metadata.input_tokens[model] = self.metadata.input_tokens.get(model, 0) + token_count
        for model, token_count in metadata_detail.output_tokens.items():
            self.metadata.output_tokens[model] = self.metadata.output_tokens.get(model, 0) + token_count

    def handle_documents(self, response: list[Document]):
        s3_keys = [doc.metadata["file_name"] for doc in response]
        files = File.objects.filter(original_file__in=s3_keys)

        for file in files:
            self.citations.append(
                (
                    file,
                    [doc for doc in response if doc.metadata["file_name"] == file.unique_name],
                )
            )
