import logging

from django.core.management import BaseCommand
from django_q.tasks import async_task

from redbox.models import Settings
from redbox_app.redbox_core.models import INACTIVE_STATUSES, File, StatusEnum
from redbox_app.worker import ingest

logger = logging.getLogger(__name__)

env = Settings()

es_client = env.elasticsearch_client()


class Command(BaseCommand):
    help = """This is an ad-hoc command when changes to the AI pipeline (e.g. a new embedding strategy)
    mean we need to regenerate chunks for all the current files.
    """

    def add_arguments(self, parser):
        """sync only to be used for testing"""
        parser.add_argument("sync", nargs="?", type=bool, default=False)

    def clean_db(self, *_args, **kwargs):  # noqa: ARG002
        """Remove all old chunk data"""
        for file in File.objects.exclude(status__in=INACTIVE_STATUSES):
            file.status = StatusEnum.processing
            file.save()

        es_client.delete_by_query(index=f"{env.elastic_root_index}-chunk", body={"query": {"match_all": {}}})

    def reingest_task(self, *_args, **kwargs):
        """Reingest files"""
        for file in File.objects.exclude(status__in=INACTIVE_STATUSES):
            logger.debug("Reingesting file object %s", file)
            async_task(ingest, file.id, task_name=file.original_file_name, group="re-ingest", sync=kwargs["sync"])

    def handle(self, *_args, **kwargs):
        self.stdout.write(self.style.NOTICE("Reingesting active files from Django"))

        async_task("self.clean_db", sync=kwargs["sync"], hook="self.reingest_task")
