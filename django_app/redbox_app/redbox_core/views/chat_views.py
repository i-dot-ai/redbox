import logging
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from http import HTTPStatus
from itertools import groupby
from operator import attrgetter
from urllib.parse import urlparse

from dataclasses_json import Undefined, dataclass_json
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from redbox_app.redbox_core.models import (AbstractAISettings, AISettings,
                                           Chat, ChatMessage, ChatRoleEnum,
                                           File, MLModel)
from yarl import URL

logger = logging.getLogger(__name__)


class ChatsView(View):
    @method_decorator(login_required)
    def get(
        self, request: HttpRequest, chat_id: uuid.UUID | None = None
    ) -> HttpResponse:

        current_user = request.user
        chat = Chat.get_ordered_by_last_message_date(current_user, [chat_id])

        messages: Sequence[ChatMessage] = []
        current_chat = None
        if chat_id:
            current_chat = get_object_or_404(Chat, id=chat_id)
            if current_chat.user != current_user:
                return redirect(reverse("chats"))
            messages = ChatMessage.get_messages_ordered_by_citation_priority(chat_id)

        parsed_url = urlparse(f"//{request.get_host()}")
        endpoint = URL.build(
            scheme=settings.WEBSOCKET_SCHEME,
            host=parsed_url.hostname,
            port=parsed_url.port,
            path=r"/ws/chat/",
        )

        completed_files, processing_files = File.get_completed_and_processing_files(
            current_user
        )

        self.decorate_selected_files(completed_files, messages)
        chat_grouped_by_date_group = groupby(chat, attrgetter("date_group"))

        ai_settings: AISettings = current_user.ai_settings
        registered_models = ai_settings.registered_models.all()
        default_model: MLModel = ai_settings.get_default_model()
        chat_model = current_chat.chat_backend if current_chat else default_model

        context = {
            "chat_id": chat_id,
            "messages": messages,
            "chat_grouped_by_date_group": chat_grouped_by_date_group,
            "current_chat": current_chat,
            "streaming": {"endpoint": str(endpoint)},
            "contact_email": settings.CONTACT_EMAIL,
            "completed_files": completed_files,
            "processing_files": processing_files,
            "chat_title_length": settings.CHAT_TITLE_LENGTH,
            "llm_options": [
                {
                    "name": registered_model.model.name,
                    "default": registered_model.model == default_model,
                    "selected": registered_model.model == chat_model,
                }
                for registered_model in registered_models
            ],
        }

        return render(
            request,
            template_name="chats.html",
            context=context,
        )

    @staticmethod
    def decorate_selected_files(
        all_files: Sequence[File], messages: Sequence[ChatMessage]
    ) -> None:
        if messages:
            last_user_message = [m for m in messages if m.role == ChatRoleEnum.user][-1]
            selected_files: Sequence[File] = (
                last_user_message.selected_files.all() or []
            )
        else:
            selected_files = []

        for file in all_files:
            file.selected = file in selected_files


class ChatsTitleView(View):
    @dataclass_json(undefined=Undefined.EXCLUDE)
    @dataclass(frozen=True)
    class Title:
        name: str

    @method_decorator(login_required)
    def post(self, request: HttpRequest, chat_id: uuid.UUID) -> HttpResponse:
        chat: Chat = get_object_or_404(Chat, id=chat_id)
        user_rating = ChatsTitleView.Title.schema().loads(request.body)

        chat.name = user_rating.name
        chat.save(update_fields=["name"])

        return HttpResponse(status=HTTPStatus.NO_CONTENT)


class UpdateChatFeedback(View):
    @method_decorator(login_required)
    def post(self, request: HttpRequest, chat_id: uuid.UUID) -> HttpResponse:
        def convert_to_boolean(value: str):
            return value == "Yes"

        chat: Chat = get_object_or_404(Chat, id=chat_id)
        chat.feedback_achieved = convert_to_boolean(request.POST.get("achieved"))
        chat.feedback_saved_time = convert_to_boolean(request.POST.get("saved_time"))
        chat.feedback_improved_work = convert_to_boolean(request.POST.get("improved_work"))
        chat.feedback_notes = request.POST.get("notes")
        chat.save()
        return HttpResponse(status=HTTPStatus.NO_CONTENT)


class DeleteChat(View):
    @method_decorator(login_required)
    def post(self, request: HttpRequest, chat_id: uuid.UUID) -> HttpResponse:  # noqa: ARG002
        chat: Chat = get_object_or_404(Chat, id=chat_id)
        chat.archived = True
        chat.save()
        return HttpResponse(status=HTTPStatus.NO_CONTENT)
