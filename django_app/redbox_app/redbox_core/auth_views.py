import os
from pathlib import Path

from django.contrib.auth import logout
from django.http import HttpRequest
from django.shortcuts import render, redirect
from dotenv import load_dotenv
from magic_link.models import MagicLink
from notifications_python_client.notifications import NotificationsAPIClient

from redbox_app.redbox_core import models

# Setup Notify
current_dir = Path(__file__).resolve().parent
dotenv_dir = current_dir.parent.parent.parent
dotenv_path = dotenv_dir / ".env"
load_dotenv()
notifications_client = NotificationsAPIClient(os.environ.get("NOTIFY_API_KEY"))


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
            link = MagicLink.objects.create(user=user)
            full_link = request.build_absolute_uri(link.get_absolute_url())

            # Email link to user
            notifications_client.send_email_notification(
                email_address=email,
                template_id="39225d39-5b90-4a5b-9a15-66a33d1256bc",
                personalisation={"link": full_link},
            )

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
