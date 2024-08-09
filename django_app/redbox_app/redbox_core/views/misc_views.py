import logging
from http import HTTPStatus

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.views.generic.base import RedirectView

from redbox_app.redbox_core.models import Chat

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def homepage_view(request):
    return render(
        request,
        template_name="homepage.html",
        context={"request": request},
    )


@require_http_methods(["GET"])
def health(_request: HttpRequest) -> HttpResponse:
    """this required by ECS Fargate"""
    return HttpResponse(status=HTTPStatus.OK)


class SecurityTxtRedirectView(RedirectView):
    """See https://github.com/alphagov/security.txt"""

    url = f"{settings.SECURITY_TXT_REDIRECT}"


@require_http_methods(["GET"])
def sitemap_view(request):
    chat_history = Chat.get_ordered_by_last_message_date(request.user) if request.user.is_authenticated else []

    return render(
        request,
        template_name="sitemap.html",
        context={"request": request, "chat_history": chat_history},
    )
