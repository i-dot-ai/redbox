from pathlib import Path

import boto3
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Exports data and uploads it to S3"

    def add_arguments(self, parser):
        parser.add_argument("--filename", type=str, default="data.json")

    def handle(self, *_args, **kwargs):
        call_command("dumpdata", "redbox_core", stdout=Path.open(Path(kwargs["filename"]), "w"))

        # Upload to S3
        s3 = boto3.client("s3")
        bucket_name = settings.AWS_STORAGE_BUCKET_NAME

        try:
            s3.upload_file(kwargs["filename"], bucket_name, kwargs["filename"])
            self.stdout.write(self.style.SUCCESS("Successfully uploaded data to S3"))
        except Exception as e:  # noqa: BLE001
            self.stdout.write(self.style.ERROR(f"Failed to upload to S3: {e}"))
