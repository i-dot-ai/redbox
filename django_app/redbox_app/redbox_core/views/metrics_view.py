from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.http import HttpResponse
import logging

logging.basicConfig(level=logging.ERROR)
@login_required
def download_metrics(_request):
    try:
        # Check if the file exists in S3
        if default_storage.exists(settings.METRICS_FILE_NAME):
            # Get the file
            file_obj = default_storage.open(settings.METRICS_FILE_NAME, "rb")
            response = HttpResponse(file_obj.read())
            response["Content-Disposition"] = f'attachment; filename="{settings.METRICS_FILE_NAME}"'
            response["Content-Type"] = "text/csv"
            return response
        else:
            return HttpResponse("File not found.", status=404)
    except Exception as e:  # noqa: BLE001
        logging.error("An error occurred while downloading metrics.", exc_info=True)
        return HttpResponse("An internal error has occurred.", status=500)
