from django.contrib.auth import logout
from django.http import HttpRequest
from django.shortcuts import render, redirect
from magic_link.models import MagicLink

from redbox_app.redbox_core import models, email_handler


def sign_in_view(request: HttpRequest):
    if request.method == "POST":
        email = request.POST.get("email")
        if not email:
            return render(
                request,
                "sign-in.html",
                {
                    "errors": {"email": "Please enter a valid email address."},
                },
            )
        email = email.lower()
        user_exists = models.User.objects.filter(email=email).exists()
        if user_exists:
            user = models.User.objects.get(email=email)
            link = MagicLink.objects.create(user=user, redirect_to="/sessions")
            full_link = request.build_absolute_uri(link.get_absolute_url())

            # Email link to user
            email_handler.send_magic_link_email(full_link, email)

        return redirect("sign-in-link-sent")
    else:
        return render(
            request,
            template_name="sign-in.html",
            context={"request": request},
        )


def sign_in_link_sent_view(request: HttpRequest):
    return render(
        request,
        template_name="sign-in-link-sent.html",
        context={"request": request},
    )


def signed_out_view(request: HttpRequest):
    logout(request)
    return render(
        request,
        template_name="signed-out.html",
        context={"request": request},
    )
