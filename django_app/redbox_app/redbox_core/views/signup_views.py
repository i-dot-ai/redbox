import logging

from django.contrib.auth import get_user_model
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views import View

from redbox_app.redbox_core.forms import SignUpForm

User = get_user_model()

logger = logging.getLogger(__name__)


class Signup1(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        form = SignUpForm()
        return render(request, "sign-up-page-1.html", {"form": form})

    def post(self, request: HttpRequest) -> HttpResponse:
        form = SignUpForm(request.POST)

        # Only allow .gov.uk email accounts
        email = request.POST.get("email")
        if not email.endswith(".gov.uk"):
            form.add_error("email", "The email must be a valid gov.uk email account")

        if form.is_valid():
            request.session["sign_up_data"] = form.cleaned_data
            return redirect("sign-up-page-2")
        else:
            return render(request, "sign-up-page-1.html", {"form": form})


class Signup2(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        form = SignUpForm()
        return render(request, "sign-up-page-2.html", {"form": form})

    def post(self, request: HttpRequest) -> HttpResponse:
        form = SignUpForm({**request.session["sign_up_data"], **request.POST})
        research_consent = request.POST.get("research_consent") == "on"
        if not research_consent:
            form.add_error("research_consent", "You must give consent to research in order to sign up to Redbox")
        if form.is_valid():
            user = User.objects.create_user(email=request.session["sign_up_data"]["email"])
            user.business_unit = request.session["sign_up_data"]["business_unit"]
            user.grade = request.session["sign_up_data"]["grade"]
            user.profession = request.session["sign_up_data"]["profession"]
            user.research_consent = research_consent
            user.save()
            return redirect("sign-in")
        else:
            return render(request, "sign-up-page-2.html", {"form": form})
