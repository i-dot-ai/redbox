import logging
import uuid
from itertools import groupby
from operator import attrgetter
from typing import ClassVar

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from redbox_core.utils import sanitize_json
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import ModelSerializer
from rest_framework.viewsets import ModelViewSet
from yarl import URL

from redbox_app.redbox_core.models import Chat, ChatLLMBackend, ChatMessage, File

logger = logging.getLogger(__name__)


class ChatsViewNew(View):
    @method_decorator(login_required)
    def get(self, request: HttpRequest) -> HttpResponse:
        chat = Chat.objects.create(
            name="New chat",
            user=request.user,
        )
        return redirect(reverse("chats", kwargs={"chat_id": chat.id}))


class ChatsView(View):
    @method_decorator(login_required)
    def get(self, request: HttpRequest, chat_id: uuid.UUID) -> HttpResponse:
        all_chats = Chat.get_ordered_by_last_message_date(request.user)
        current_chat = get_object_or_404(Chat, id=chat_id)
        if current_chat.user != request.user:
            return redirect(reverse("chats"))
        messages = ChatMessage.get_messages(chat_id)

        endpoint = URL.build(
            scheme=settings.WEBSOCKET_SCHEME,
            host="localhost" if settings.ENVIRONMENT.is_test else settings.ENVIRONMENT.hosts[0],
            port=int(request.META["SERVER_PORT"]) if settings.ENVIRONMENT.is_test else None,
            path=f"/ws/chat/{chat_id}",
        )

        completed_files, processing_files = File.get_completed_and_processing_files(chat_id)

        chat_grouped_by_date_group = groupby(all_chats, attrgetter("date_group"))

        chat_backend = current_chat.chat_backend if current_chat else ChatLLMBackend.objects.get(is_default=True)

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
                    "name": str(chat_llm_backend),
                    "default": chat_llm_backend.is_default,
                    "selected": chat_llm_backend == chat_backend,
                    "id": chat_llm_backend.id,
                    "description": chat_llm_backend.description,
                    "max_tokens": chat_llm_backend.context_window_size,
                }
                for chat_llm_backend in ChatLLMBackend.objects.filter(enabled=True).order_by("enabled", "name")
            ],
        }

        return render(
            request,
            template_name="chats.html",
            context=context,
        )


class ChatSerializer(ModelSerializer):
    class Meta:
        model = Chat
        fields = "__all__"

    def to_internal_value(self, data):
        data = sanitize_json(data)
        return super().to_internal_value(data)


class ChatViewSet(ModelViewSet):
    serializer_class = ChatSerializer
    queryset = Chat.objects.all()
    permission_classes: ClassVar = [IsAuthenticated]
    lookup_url_kwarg = "chat_id"
