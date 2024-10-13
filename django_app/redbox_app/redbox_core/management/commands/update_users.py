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

    def handle(self, *_args, **kwargs):
        obj = File.objects.get(id=kwargs["file_id"])

        for line in obj.original_file.open("r"):
            json_row = json.loads(line)

            def f(value):
                if isinstance(value, str) and " - " in value:
                    return value.split("-")[0][:-1]
                return value

            json_row = {k: f(v) for k, v in json_row.items()}

            try:
                user = USER.objects.get(email=json_row["email"])
                for k, v in json_row.items():
                    setattr(user, k, v)
                user.save()
            except USER.DoesNotExist:
                try:
                    USER.objects.create(**json_row)
                except Exception as e:  # noqa: BLE001
                    logger.error("failed to set %s because %s", json_row, e)  # noqa: TRY400
