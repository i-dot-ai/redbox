import logging
import uuid
from http import HTTPStatus

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views import View

from redbox_app.redbox_core.forms import RatingsForm
from redbox_app.redbox_core.models import ChatMessage

logger = logging.getLogger(__name__)


class RatingsView(View):
    @method_decorator(login_required)
    def post(self, request: HttpRequest, message_id: uuid.UUID) -> HttpResponse:
        chat_message = get_object_or_404(ChatMessage, id=message_id)
        form = RatingsForm(request.POST, instance=chat_message)
        if form.is_valid():
            form.save()
            return HttpResponse(status=HTTPStatus.NO_CONTENT)
        return HttpResponse(status=HTTPStatus.BAD_REQUEST)
