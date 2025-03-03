"""
Views for info pages like privacy notice, accessibility statement, etc.
These shouldn't contain sensitive data and don't require login.
"""

from django.shortcuts import render
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET"])
def training_welcome_view(request):
    return render(
        request,
        "/training/training-welcome.html",
        {},
    )


@require_http_methods(["GET"])
def training_chat_view(request):
    return render(
        request,
        "/training/training-chat.html",
        {},
    )


@require_http_methods(["GET"])
def training_documents_view(request):
    return render(
        request,
        "/training/training-documents.html",
        {},
    )


@require_http_methods(["GET"])
def training_models_view(request):
    return render(
        request,
        "/training/training-models.html",
        {},
    )
