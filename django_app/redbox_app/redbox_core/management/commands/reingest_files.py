import logging

from django.core.management import BaseCommand

from redbox_app.redbox_core.models import File

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = """This is an ad-hoc command when changes to the AI pipeline (e.g. a new embedding strategy)
    mean we need to regenerate chunks for all the current files.
    """

    def add_arguments(self, parser):
        """sync only to be used for testing"""
        parser.add_argument("sync", nargs="?", type=bool, default=False)

    def handle(self, *_args, **_kwargs):
        self.stdout.write(self.style.NOTICE("Reingesting active files from Django"))

        for file in File.objects.exclude(status=File.Status.errored):
            logger.debug("Reingesting file object %s", file)
            file.ingest()
