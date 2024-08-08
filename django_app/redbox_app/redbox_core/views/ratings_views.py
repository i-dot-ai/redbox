import logging
import uuid
from dataclasses import dataclass, field
from http import HTTPStatus

from dataclasses_json import Undefined, dataclass_json
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views import View

from redbox_app.redbox_core.models import (
    ChatMessage,
    ChatMessageRating,
)

logger = logging.getLogger(__name__)


class RatingsView(View):
    @dataclass_json(undefined=Undefined.EXCLUDE)
    @dataclass(frozen=True)
    class Rating:
        rating: int
        text: str | None = None
        chips: set[str] = field(default_factory=set)

    @method_decorator(login_required)
    def post(self, request: HttpRequest, message_id: uuid.UUID) -> HttpResponse:
        message: ChatMessage = get_object_or_404(ChatMessage, id=message_id)
        user_rating = RatingsView.Rating.schema().loads(request.body)

        chat_message_rating: ChatMessageRating
        if chat_message_rating := ChatMessageRating.objects.filter(chat_message=message).first():
            chat_message_rating.rating = user_rating.rating
            chat_message_rating.text = user_rating.text
            chat_message_rating.chips = user_rating.chips
            chat_message_rating.save()
        else:
            chat_message_rating = ChatMessageRating(
                chat_message=message, rating=user_rating.rating, text=user_rating.text, chips=user_rating.chips
            )
            chat_message_rating.save()
        return HttpResponse(status=HTTPStatus.NO_CONTENT)
