import logging
import os

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from redbox_app.redbox_core.client import CoreApiClient
from redbox_app.redbox_core.models import (
    ChatHistory,
    ChatMessage,
    ChatRoleEnum,
    File,
    ProcessingStatusEnum,
)
from yarl import URL

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")

CHUNK_SIZE = 1024
# move this somewhere
APPROVED_FILE_EXTENSIONS = [
    ".eml",
    ".html",
    ".json",
    ".md",
    ".msg",
    ".rst",
    ".rtf",
    ".txt",
    ".xml",
    ".csv",
    ".doc",
    ".docx",
    ".epub",
    ".epub",
    ".odt",
    ".pdf",
    ".ppt",
    ".pptx",
    ".tsv",
    ".xlsx",
    ".htm",
]
MAX_FILE_SIZE = 209715200  # 200 MB or 200 * 1024 * 1024


@require_http_methods(["GET"])
def homepage_view(request):
    return render(
        request,
        template_name="homepage.html",
        context={"request": request},
    )


@login_required
def documents_view(request):
    files = File.objects.filter(user=request.user)

    return render(
        request,
        template_name="documents.html",
        context={"request": request, "files": files},
    )


def get_file_extension(file):
    # TODO: use a third party checking service to validate this

    _, extension = os.path.splitext(file.name)
    return extension


@login_required
def upload_view(request):
    errors = {"upload_doc": []}
    uploaded = False

    if request.method == "POST" and request.FILES["uploadDoc"]:
        # https://django-storages.readthedocs.io/en/1.13.2/backends/amazon-S3.html
        uploaded_file = request.FILES["uploadDoc"]

        file_extension = get_file_extension(uploaded_file)

        if uploaded_file.name is None:
            errors["upload_doc"].append("File has no name")
        if uploaded_file.content_type is None:
            errors["upload_doc"].append("File has no content-type")
        if uploaded_file.size > MAX_FILE_SIZE:
            errors["upload_doc"].append("File is larger than 200MB")
        if file_extension not in APPROVED_FILE_EXTENSIONS:
            errors["upload_doc"].append(f"File type {file_extension} not supported")

        if not len(errors["upload_doc"]):
            # ingest file
            api = CoreApiClient(host=settings.CORE_API_HOST, port=settings.CORE_API_PORT)

            try:
                api.upload_file(settings.BUCKET_NAME, uploaded_file.name, request.user)
                file = File.objects.create(
                    processing_status=ProcessingStatusEnum.uploaded.value,
                    user=request.user,
                    original_file=uploaded_file,
                    original_file_name=uploaded_file.name,
                )
                file.save()
                # TODO: update improved File object with elastic uuid
                uploaded = True
            except ValueError as value_error:
                errors["upload_doc"].append(value_error.args[0])

    return render(
        request,
        template_name="upload.html",
        context={"request": request, "errors": errors, "uploaded": uploaded},
    )


@login_required
def remove_doc_view(request, doc_id: str):
    file = File.objects.get(pk=doc_id)
    if request.method == "POST":
        logger.info("Removing document: %s", request.POST["doc_id"])
        file.delete()
        return redirect("documents")
    return render(
        request,
        template_name="remove-doc.html",
        context={"request": request, "doc_id": doc_id, "doc_name": file.name},
    )


@login_required
def sessions_view(request: HttpRequest, session_id: str = ""):
    chat_history = ChatHistory.objects.all().filter(users=request.user)

    messages = []
    if session_id:
        messages = ChatMessage.objects.filter(chat_history__id=session_id)
    endpoint = URL.build(scheme="ws", host=request.get_host(), path=r"/ws/chat/")
    context = {
        "session_id": session_id,
        "messages": messages,
        "chat_history": chat_history,
        "streaming": {"in_use": settings.USE_STREAMING, "endpoint": str(endpoint)},
    }

    return render(
        request,
        template_name="sessions.html",
        context=context,
    )


@require_http_methods(["POST"])
def post_message(request: HttpRequest) -> HttpResponse:
    message_text = request.POST.get("message", "New chat")

    # get current session, or create a new one
    if session_id := request.POST.get("session-id", None):
        session = ChatHistory.objects.get(id=session_id)
    else:
        session_name = message_text[0:20]
        session = ChatHistory(name=session_name, users=request.user)
        session.save()

    # save user message
    chat_message = ChatMessage(chat_history=session, text=message_text, role=ChatRoleEnum.user)
    chat_message.save()

    # get LLM response
    message_history = [
        {"role": message.role, "text": message.text}
        for message in ChatMessage.objects.all().filter(chat_history=session)
    ]
    core_api = CoreApiClient(host=settings.CORE_API_HOST, port=settings.CORE_API_PORT)
    output_text = core_api.rag_chat(message_history, request.user.get_bearer_token())

    # save LLM response
    llm_message = ChatMessage(chat_history=session, text=output_text, role=ChatRoleEnum.ai)
    llm_message.save()

    return redirect(reverse(sessions_view, args=(session.id,)))


@require_http_methods(["GET"])
def health(_request: HttpRequest) -> HttpResponse:
    """this required by ECS Fargate"""
    return HttpResponse(status=200)
