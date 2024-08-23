import logging

from django.core.management import BaseCommand
from django_q.tasks import async_task

from redbox_app.redbox_core.models import INACTIVE_STATUSES, File
from redbox_app.worker import ingest

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = """This is an ad-hoc command when changes to the AI pipeline (e.g. a new embedding strategy)
    mean we need to regenerate chunks for all the current files.

    It attempts to reupload file data to core-api for reingestion."""

    def add_arguments(self, parser):
        """sync only to be used for testing"""
        parser.add_argument("sync", nargs="?", type=bool, default=False)

    def handle(self, *_args, **kwargs):
        self.stdout.write(self.style.NOTICE("Reingesting active files from Django"))

        for file in File.objects.exclude(status__in=INACTIVE_STATUSES):
            logger.debug("Reingesting file object %s", file)
            async_task(ingest, file.id, task_name=file.original_file_name, group="re-ingest", sync=kwargs["sync"])
