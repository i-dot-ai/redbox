import logging
import uuid
from collections.abc import MutableSequence, Sequence
from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import FieldError, ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_http_methods

from redbox_app.redbox_core.models import File

User = get_user_model()
logger = logging.getLogger(__name__)
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


class UploadView(View):
    @method_decorator(login_required)
    def post(self, request: HttpRequest, chat_id: uuid.UUID) -> HttpResponse:
        errors: MutableSequence[str] = []

        uploaded_files: MutableSequence[UploadedFile] = request.FILES.getlist("uploadDocs")

        if not uploaded_files:
            errors.append("No document selected")

        for uploaded_file in uploaded_files:
            errors += self.validate_uploaded_file(uploaded_file)

        if not errors:
            for uploaded_file in uploaded_files:
                # ingest errors are handled differently, as the other documents have started uploading by this point
                file, request.session["ingest_errors"] = self.ingest_file(uploaded_file, request.user, chat_id)

        # This can be removed once we are uploading docs only on the chat page:
        if not errors and not chat_id:
            return redirect(reverse("documents"))

        return self.build_response(request, errors)

    @staticmethod
    def validate_uploaded_file(uploaded_file: UploadedFile) -> Sequence[str]:
        errors: MutableSequence[str] = []

        if not uploaded_file.name:
            errors.append("File has no name")
        else:
            file_extension = Path(uploaded_file.name).suffix
            if file_extension.lower() not in APPROVED_FILE_EXTENSIONS:
                errors.append(f"Error with {uploaded_file.name}: File type {file_extension} not supported")

        if not uploaded_file.content_type:
            errors.append(f"Error with {uploaded_file.name}: File has no content-type")

        if uploaded_file.size > MAX_FILE_SIZE:
            errors.append(f"Error with {uploaded_file.name}: File is larger than 200MB")

        return errors

    @staticmethod
    def ingest_file(uploaded_file: UploadedFile, chat_id: uuid.UUID) -> tuple[File, Sequence[str]]:
        try:
            logger.info("getting file from s3")
            file = File.objects.create(
                status=File.Status.processing.value,
                original_file=uploaded_file,
                chat_id=chat_id,
            )
        except (ValueError, FieldError, ValidationError) as e:
            logger.exception("Error creating File model object for %s.", uploaded_file, exc_info=e)
            return None, e.args

        file.ingest()

        return file, []


@login_required
def remove_doc_view(request, chat_id: uuid.UUID, doc_id: uuid.UUID):
    file = get_object_or_404(File, id=doc_id, chat_id=chat_id)

    if request.method == "POST":
        logger.info("Removing document: %s", request.POST["doc_id"])
        file.delete()

    return JsonResponse({"status": file.get_status_text()})


@require_http_methods(["GET"])
@login_required
def file_status_api_view(request: HttpRequest) -> JsonResponse:
    file_id = request.GET.get("id", None)
    if not file_id:
        logger.error("Error getting file object information - no file ID provided %s.")
        return JsonResponse({"status": File.Status.errored.label})
    try:
        file: File = get_object_or_404(File, id=file_id)
    except File.DoesNotExist as ex:
        logger.exception("File object information not found in django - file does not exist %s.", file_id, exc_info=ex)
        return JsonResponse({"status": File.Status.errored.label})
    return JsonResponse(
        {"status": file.get_status_text(), "position_in_queue": file.position_in_queue(), "tokens": file.token_count}
    )
