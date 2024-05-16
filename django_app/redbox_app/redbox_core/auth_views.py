import logging
from typing import Optional

from django.contrib.auth import logout
from django.http import HttpRequest
from django.shortcuts import redirect, render
from magic_link.models import MagicLink
from redbox_app.redbox_core import email_handler, models
from redbox_app.redbox_core.forms import SignInForm

logger = logging.getLogger(__name__)


def get_or_create_user(email: str) -> Optional[models.User]:
    try:
        return models.User.objects.get(email=email)
    except models.User.DoesNotExist:
        if email.endswith("@cabinetoffice.gov.uk"):
            logger.debug("creating user with email %s", email)
            return models.User.objects.create(email=email)
        else:
            logger.error("rejecting user with email %s", email)
    return None


def sign_in_view(request: HttpRequest):
    if request.user.is_authenticated:
        return redirect("homepage")
    if request.method == "POST":
        form = SignInForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].lower()

            if user := get_or_create_user(email):
                link = MagicLink.objects.create(user=user, redirect_to="/")
                full_link = request.build_absolute_uri(link.get_absolute_url())

                # Email link to user
                email_handler.send_magic_link_email(full_link, email)
            else:
                logger.debug("User with email %s not found", email)

            return redirect("sign-in-link-sent")

        return render(
            request,
            template_name="sign-in.html",
            context={
                "errors": form.errors,
            },
        )

    return render(
        request,
        template_name="sign-in.html",
        context={"request": request},
    )


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
