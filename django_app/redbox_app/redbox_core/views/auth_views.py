import logging

from django.contrib.auth import get_user_model, logout
from django.http import HttpRequest
from django.shortcuts import redirect

logger = logging.getLogger(__name__)
User = get_user_model()


def signed_out_view(request: HttpRequest):
    logout(request)
    return redirect("homepage")
