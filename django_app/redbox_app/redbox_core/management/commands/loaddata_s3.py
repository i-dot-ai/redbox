import boto3
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Loads data from S3 into the database"

    def add_arguments(self, parser):
        parser.add_argument("--filename", type=str, default="data.json")

    def handle(self, *_args, **kwargs):
        bucket_name = settings.AWS_STORAGE_BUCKET_NAME

        s3 = boto3.client("s3")
        s3.download_file(bucket_name, kwargs["filename"], kwargs["filename"])

        try:
            call_command("loaddata", kwargs["filename"])
        except Exception as e:  # noqa: BLE001
            self.stdout.write(self.style.ERROR(f"Failed to load data into the database: {e}"))
