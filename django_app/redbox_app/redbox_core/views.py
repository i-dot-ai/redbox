import os
import uuid

import requests
from boto3.s3.transfer import TransferConfig
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from redbox_app.redbox_core.client import CoreApiClient, s3_client
from redbox_app.redbox_core.models import ChatHistory, ChatMessage, ChatRoleEnum, File, ProcessingStatusEnum

s3 = s3_client()
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
    # Testing with dummy data for now
    if not File.objects.exists():
        File.objects.create(
            name="Document 1",
            path="#download1",
            processing_status=ProcessingStatusEnum.complete,
        )
        File.objects.create(
            name="Document 2",
            path="#download2",
            processing_status=ProcessingStatusEnum.parsing,
        )

    # Add processing_text
    files = File.objects.all()
    for file in files:
        file.processing_text = file.get_processing_text()

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
            file_key = f"{uuid.uuid4()}{file_extension}"

            # TODO: can we upload chunks instead of having the file read?
            s3.upload_fileobj(
                Bucket=settings.BUCKET_NAME,
                Fileobj=uploaded_file,
                Key=file_key,
                ExtraArgs={"Tagging": f"file_type={uploaded_file.content_type}"},
                Config=TransferConfig(
                    multipart_chunksize=CHUNK_SIZE,
                    preferred_transfer_client="auto",
                    multipart_threshold=CHUNK_SIZE,
                    use_threads=True,
                    max_concurrency=80,
                ),
            )

            # ingest file
            api = CoreApiClient(host=settings.CORE_API_HOST, port=settings.CORE_API_PORT)

            try:
                api.upload_file(uploaded_file.name, request.user)
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
    if request.method == "POST":
        print(f"Removing document: {request.POST['doc_id']}")
        # TO DO: handle document deletion here

    # Hard-coding document name for now, just to flag that this is needed in the template
    doc_name = "Document X"
    return render(
        request,
        template_name="remove-doc.html",
        context={"request": request, "doc_id": doc_id, "doc_name": doc_name},
    )


@login_required
def sessions_view(request, session_id: str = ""):
    USE_STREAMING = True
    STREAMING_ENDPOINT = "ws://localhost:8090/ws/chat/"

    chat_history = ChatHistory.objects.all().filter(users=request.user)

    messages = []
    if session_id:
        messages = ChatMessage.objects.filter(chat_history__id=session_id)

    context = {
        "session_id": session_id,
        "messages": messages,
        "chat_history": chat_history,
        "streaming": {
            "in_use": USE_STREAMING,
            "endpoint": STREAMING_ENDPOINT
        }
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
    if session_id := request.POST.get("session-id", ""):
        session = ChatHistory.objects.get(id=session_id)
    else:
        session_name = message_text[0:20]
        session = ChatHistory(name=session_name, users=request.user)
        session.save()
        session_id = session.id

    # save user message
    chat_message = ChatMessage(chat_history=session, text=message_text, role=ChatRoleEnum.user)
    chat_message.save()

    # get LLM response
    message_history = [
        {"role": message.role, "text": message.text}
        for message in ChatMessage.objects.all().filter(chat_history=session)
    ]
    url = settings.CORE_API_HOST + ":" + settings.CORE_API_PORT + "/chat/rag"
    response = requests.post(
        url, json={"message_history": message_history}, headers={"Authorization": request.user.get_bearer_token()}
    )
    llm_data = response.json()

    # save LLM response
    llm_message = ChatMessage(chat_history=session, text=llm_data["output_text"], role=ChatRoleEnum.ai)
    llm_message.save()

    return redirect(reverse(sessions_view, args=(session_id,)))
