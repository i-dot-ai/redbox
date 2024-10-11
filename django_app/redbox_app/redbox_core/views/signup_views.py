import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpRequest, HttpResponse, QueryDict
from django.shortcuts import redirect, render
from django.views import View

from redbox_app.redbox_core.forms import SignUpForm

User = get_user_model()

logger = logging.getLogger(__name__)


class AbstractSignup(View):
    current_page = None
    next_page = None

    def get(self, request: HttpRequest) -> HttpResponse:
        if not settings.ALLOW_SIGN_UPS:
            return redirect("homepage")
        form = SignUpForm()
        return render(request, f"{self.current_page}.html", {"form": form})

    def post(self, request: HttpRequest) -> HttpResponse:
        if not settings.ALLOW_SIGN_UPS:
            return redirect("homepage")
        combined_data = {**request.session.get("sign_up_data", {}), **request.POST.dict()}
        query_dict = QueryDict("", mutable=True)
        query_dict.update(combined_data)
        form = SignUpForm(query_dict)

        if form.is_valid():
            request.session["sign_up_data"] = form.cleaned_data
            return redirect(self.next_page)
        else:
            return render(request, f"{self.current_page}.html", {"form": form})


class Signup1(AbstractSignup):
    current_page = "sign-up-page-1"
    next_page = "sign-up-page-2"

    def post(self, request: HttpRequest) -> HttpResponse:
        if not settings.ALLOW_SIGN_UPS:
            return redirect("homepage")
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


class Signup2(AbstractSignup):
    current_page = "sign-up-page-2"
    next_page = "sign-up-page-3"


class Signup3(AbstractSignup):
    current_page = "sign-up-page-3"
    next_page = "sign-up-page-4"


class Signup4(AbstractSignup):
    current_page = "sign-up-page-4"
    next_page = "sign-up-page-5"


class Signup5(AbstractSignup):
    current_page = "sign-up-page-5"
    next_page = "sign-up-page-6"


class Signup6(AbstractSignup):
    current_page = "sign-up-page-6"
    next_page = "sign-up-page-7"

    def post(self, request: HttpRequest) -> HttpResponse:
        if not settings.ALLOW_SIGN_UPS:
            return redirect("homepage")
        combined_data = {**request.session.get("sign_up_data", {}), **request.POST.dict()}
        query_dict = QueryDict("", mutable=True)
        query_dict.update(combined_data)
        form = SignUpForm(query_dict)

        required_fields = [
            "consent_research",
            "consent_interviews",
            "consent_feedback",
            "consent_condfidentiality",
            "consent_understand",
            "consent_agreement",
        ]
        for field in required_fields:
            if request.POST.get(field) != "on":
                form.add_error(field, "You must give consent in order to sign up to Redbox")

        if form.is_valid():
            user = User.objects.create_user(email=request.session["sign_up_data"]["email"])
            for field_name, field_value in form.cleaned_data.items():
                setattr(user, field_name, field_value)
            user.save()
            return redirect("sign-up-page-7")
        else:
            return render(request, "sign-up-page-6.html", {"form": form})


class Signup7(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        if not settings.ALLOW_SIGN_UPS:
            return redirect("homepage")
        return render(request, "sign-up-page-7.html")
