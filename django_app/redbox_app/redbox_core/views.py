import os
import uuid
import requests

from boto3.s3.transfer import TransferConfig
from django.conf import settings
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from redbox_app.redbox_core.client import CoreApiClient, s3_client
from redbox_app.redbox_core.models import File, ProcessingStatusEnum

from dotenv import load_dotenv

load_dotenv()

from . import models  # noqa: E402

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
                api.upload_file(uploaded_file.name)
                # TODO: update improved File object with elastic uuid
                uploaded = True
            except ValueError as value_error:
                errors["upload_doc"].append(value_error.args[0])

    return render(
        request,
        template_name="upload.html",
        context={"request": request, "errors": errors, "uploaded": uploaded},
    )


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


def sessions_view(request, session_id: str = ""):
    chat_history = models.ChatHistory.objects.all().filter(users=request.user)

    messages = []
    if session_id:
        current_chat = models.ChatHistory.objects.get(id=session_id)
        messages = models.ChatMessage.objects.all().filter(chat_history=current_chat)

    context = {
        "session_id": session_id,
        "messages": messages,
        "chat_history": chat_history,
    }

    return render(
        request,
        template_name="sessions.html",
        context=context,
    )


@require_http_methods(["POST"])
def post_message(request):
    message_text = request.POST.get("message", "New chat")

    # get current session, or create a new one
    if session_id := request.POST.get("session-id", ""):
        session = models.ChatHistory.objects.get(id=session_id)
    else:
        session_name = message_text[0:20]
        session = models.ChatHistory(name=session_name, users=request.user)
        session.save()
        session_id = session.id

    # save user message
    chat_message = models.ChatMessage(chat_history=session, text=message_text, role=models.ChatRoleEnum.user)
    chat_message.save()

    # get LLM response
    message_history = [
        {"role": message.role, "text": message.text}
        for message in models.ChatMessage.objects.all().filter(chat_history=session)
    ]
    url = os.environ.get("CORE_API_HOST") + ":" + os.environ.get("CORE_API_PORT") + "/chat/rag"
    response = requests.post(url, json={"message_history": message_history})
    llm_data = response.json()

    # save LLM response
    llm_message = models.ChatMessage(
        chat_history=session, text=llm_data["response_message"]["text"], role=models.ChatRoleEnum.ai
    )
    llm_message.save()

    return redirect(reverse(sessions_view, args=(session_id,)))
