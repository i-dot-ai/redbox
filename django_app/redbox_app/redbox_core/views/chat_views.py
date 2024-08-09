import logging
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from http import HTTPStatus
from itertools import groupby
from operator import attrgetter

from dataclasses_json import Undefined, dataclass_json
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_http_methods
from yarl import URL

from redbox_app.redbox_core.client import CoreApiClient
from redbox_app.redbox_core.models import Chat, ChatMessage, ChatRoleEnum, Citation, File

logger = logging.getLogger(__name__)
core_api = CoreApiClient(host=settings.CORE_API_HOST, port=settings.CORE_API_PORT)


class ChatsView(View):
    @method_decorator(login_required)
    def get(self, request: HttpRequest, chat_id: uuid.UUID | None = None) -> HttpResponse:
        chat = Chat.get_ordered_by_last_message_date(request.user, [chat_id])

        messages: Sequence[ChatMessage] = []
        current_chat = None
        if chat_id:
            current_chat = get_object_or_404(Chat, id=chat_id)
            if current_chat.user != request.user:
                return redirect(reverse("chats"))
            messages = ChatMessage.get_messages_ordered_by_citation_priority(chat_id)
        endpoint = URL.build(scheme=settings.WEBSOCKET_SCHEME, host=request.get_host(), path=r"/ws/chat/")

        completed_files, processing_files = File.get_completed_and_processing_files(request.user)

        self.decorate_selected_files(completed_files, messages)
        chat_grouped_by_date_group = groupby(chat, attrgetter("date_group"))

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
        }

        return render(
            request,
            template_name="chats.html",
            context=context,
        )

    @staticmethod
    def decorate_selected_files(all_files: Sequence[File], messages: Sequence[ChatMessage]) -> None:
        if messages:
            last_user_message = [m for m in messages if m.role == ChatRoleEnum.user][-1]
            selected_files: Sequence[File] = last_user_message.selected_files.all() or []
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


@require_http_methods(["POST"])
def post_message(request: HttpRequest) -> HttpResponse:
    message_text = request.POST.get("message", "New chat")
    selected_file_uuids: Sequence[uuid.UUID] = [uuid.UUID(v) for k, v in request.POST.items() if k.startswith("file-")]

    # get current session, or create a new one
    if session_id := request.POST.get("session-id", None):
        session = Chat.objects.get(id=session_id)
    else:
        session_name = message_text[0 : settings.CHAT_TITLE_LENGTH]
        session = Chat(name=session_name, user=request.user)
        session.save()

    selected_files = File.objects.filter(id__in=selected_file_uuids, user=request.user)

    # save user message
    user_message = ChatMessage(chat=session, text=message_text, role=ChatRoleEnum.user)
    user_message.save()
    user_message.selected_files.set(selected_files)

    # get LLM response
    message_history = [
        {"role": message.role, "text": message.text} for message in ChatMessage.objects.all().filter(chat=session)
    ]
    selected_files_message = [{"uuid": str(f.core_file_uuid)} for f in selected_files]
    response_data = core_api.rag_chat(message_history, selected_files_message, request.user)

    llm_message = ChatMessage(chat=session, text=response_data.output_text, role=ChatRoleEnum.ai)
    llm_message.save()

    doc_uuids: list[uuid.UUID] = [doc.file_uuid for doc in response_data.source_documents]
    files: list[File] = File.objects.filter(core_file_uuid__in=doc_uuids, user=request.user)

    for file in files:
        file.last_referenced = timezone.now()
        file.save()

    for doc in response_data.source_documents:
        new_citation = Citation(
            file=File.objects.get(core_file_uuid=doc.file_uuid), chat_message=llm_message, text=doc.page_content
        )
        new_citation.save()

    return redirect(reverse("chats", args=(session.id,)))
