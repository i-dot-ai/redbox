import logging

from django.contrib.auth import logout
from django.http import HttpRequest
from django.shortcuts import redirect, render
from magic_link.models import MagicLink
from redbox_app.redbox_core import email_handler, models
from redbox_app.redbox_core.forms import SignInForm
from requests import HTTPError

logger = logging.getLogger(__name__)


def sign_in_view(request: HttpRequest):
    if request.user.is_authenticated:
        return redirect("homepage")
    
    return redirect("/auth/login")


def sign_in_link_sent_view(request: HttpRequest):
    if request.user.is_authenticated:
        return redirect("homepage")
    return render(
        request,
        template_name="sign-in-link-sent.html",
        context={"request": request},
    )


def signed_out_view(request: HttpRequest):
    logout(request)
    return redirect("homepage")
