import logging
import uuid

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View

from redbox_app.redbox_core.client import CoreApiClient
from redbox_app.redbox_core.models import ChatMessage, File

logger = logging.getLogger(__name__)
core_api = CoreApiClient(host=settings.CORE_API_HOST, port=settings.CORE_API_PORT)


class CitationsView(View):
    @method_decorator(login_required)
    def get(self, request: HttpRequest, message_id: uuid.UUID | None = None) -> HttpResponse:
        message = get_object_or_404(ChatMessage, id=message_id)

        if message.chat.user != request.user:
            return redirect(reverse("chats"))

        source_files = File.get_ordered_by_citation_priority(message_id)

        context = {"message": message, "source_files": source_files}

        return render(
            request,
            template_name="citations.html",
            context=context,
        )
