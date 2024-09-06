import logging
import json

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import UpdateView
from http import HTTPStatus

from redbox_app.redbox_core.forms import DemographicsForm

User = get_user_model()

logger = logging.getLogger(__name__)


class CheckDemographicsView(View):
    @method_decorator(login_required)
    def get(self, request: HttpRequest) -> HttpResponse:
        user: User = request.user
        if all([user.name, user.ai_experience]):
            return redirect("chats")
        else:
            return redirect("demographics")


class DemographicsView(LoginRequiredMixin, UpdateView):
    model = User
    template_name = "demographics.html"
    form_class = DemographicsForm
    success_url = "/chats/"

    def get_object(self, **kwargs):  # noqa: ARG002
        return self.request.user


class UpdateDemographicsView(View):
    @method_decorator(login_required)
    def post(self, request: HttpRequest) -> HttpResponse:
        user: User = request.user
        data = json.loads(request.body.decode("utf-8"))

        print(data)
        user.name = data["name"]
        user.ai_experience = data["ai_experience"]
        user.info_about_user = data["info_about_user"]
        user.redbox_response_preferences = data["redbox_response_preferences"]

        return HttpResponse(status=HTTPStatus.NO_CONTENT)