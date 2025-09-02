import logging

from django.contrib.auth import get_user_model, logout
from django.http import HttpRequest
from django.shortcuts import redirect

logger = logging.getLogger(__name__)
User = get_user_model()


def oauth_login_view(request: HttpRequest):
    if request.user.is_authenticated:
        return redirect("homepage")

    # Ensure session exists before OAuth2 redirect to prevent AuthStateMissing error
    request.session.save()

    return redirect("social:begin", "oidc")


def signed_out_view(request: HttpRequest):
    logout(request)
    return redirect("homepage")
