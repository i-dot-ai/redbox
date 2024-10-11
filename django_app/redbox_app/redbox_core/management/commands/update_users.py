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
        """sync only to be used for testing"""
        parser.add_argument("file-id", nargs="1", type=str)

    def handle(self, *_args, **kwargs):
        obj = File.objects.get(id=kwargs["file-id"])
        rows = obj.file.open("r").readlines()

        for row in rows:
            json_row = json.loads(row)
            try:
                USER.objects.update_or_create(**json_row)
            except Exception as e:  # noqa: BLE001
                logger.error("failed to update_or_create %s because %s", json_row["email"], e)  # noqa: TRY400
