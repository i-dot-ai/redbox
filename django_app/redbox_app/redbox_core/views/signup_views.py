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
            if business_unit := form.cleaned_data.get("business_unit"):
                form.cleaned_data["business_unit"] = str(business_unit.pk)
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
        allowed_emails = settings.ALLOWED_EMAIL_DOMAINS
        if not any(email.endswith(allowed_email) for allowed_email in allowed_emails):
            form.add_error("email", "The email must be a valid email account")

        if form.is_valid():
            if business_unit := form.cleaned_data.get("business_unit"):
                form.cleaned_data["business_unit"] = str(business_unit.pk)
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
            return redirect("sign-up-page-4")
        else:
            return render(request, "sign-up-page-3.html", {"form": form})


class Signup4(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        if not settings.ALLOW_SIGN_UPS:
            return redirect("homepage")
        return render(request, "sign-up-page-4.html", {"contact_email": settings.CONTACT_EMAIL})
