import json
import logging

from django.contrib.auth import get_user_model
from django.core.management import BaseCommand

from redbox_app.redbox_core.models import File

USER = get_user_model()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = """This should be used to bulk update user data."""

    def add_arguments(self, parser):
        """id of file to use for update"""
        parser.add_argument("file_id", nargs=None, type=str)
        parser.add_argument("create", nargs=None, type=bool, default=True)

    def handle(self, *_args, **kwargs):
        obj = File.objects.get(id=kwargs["file_id"])

        for line in obj.original_file.open("r"):
            json_row = json.loads(line)

            def extract_value(value):
                """hack to get around values like "Monthly - a few times per month" """
                if isinstance(value, str) and " - " in value:
                    return value.split("-")[0][:-1]
                return value

            json_row = {k: extract_value(v) for k, v in json_row.items()}

            if USER.objects.filter(email=json_row["email"]).exists():
                USER.objects.filter(email=json_row["email"]).update(**json_row)
            elif kwargs["create"]:
                USER.objects.create(**json_row)
