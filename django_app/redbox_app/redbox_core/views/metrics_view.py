import logging

from botocore.exceptions import ClientError
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse

from redbox.models import Settings

logging.basicConfig(level=logging.ERROR)
env = Settings()
s3_client = env.s3_client()


@login_required
def download_metrics(_request, file_name: str = settings.METRICS_FILE_NAME):
    try:
        file_obj = s3_client.get_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=file_name)["Body"]
        response = HttpResponse(file_obj.read())
        response["Content-Disposition"] = f'attachment; filename="{file_name}"'
        response["Content-Type"] = "text/csv"
    except ClientError as e:
        if (
            e.args[0]
            == "An error occurred (NoSuchKey) when calling the GetObject operation: The specified key does not exist."
        ):
            return HttpResponse("File not found.", status=404)
        return HttpResponse(status=500)
    else:
        return response
