import logging
import time

from django.core.management import BaseCommand
from django_q.tasks import async_task

from redbox.models.settings import get_settings
from redbox_app.redbox_core.models import File
from redbox_app.worker import ingest

logger = logging.getLogger(__name__)

env = get_settings()

es_client = env.elasticsearch_client()


def switch_aliases(alias, new_index):
    try:
        response = es_client.indices.get_alias(name=alias)
        indices_to_remove = list(response)
    except Exception as e:
        logger.exception("Error fetching alias", exc_info=e)

    actions = [{"remove": {"index": index, "alias": alias}} for index in indices_to_remove]
    actions.append({"add": {"index": new_index, "alias": alias}})

    es_client.indices.update_aliases(body={"actions": actions})


class Command(BaseCommand):
    help = """This is an ad-hoc command when changes to the AI pipeline (e.g. a new embedding strategy)
    mean we need to regenerate chunks for all the current files.
    """

    def add_arguments(self, parser):
        """sync only to be used for testing"""
        parser.add_argument("sync", nargs="?", type=bool, default=False)

    def handle(self, *_args, **kwargs):
        self.stdout.write(self.style.NOTICE("Reingesting active files from Django"))

        new_index = f"{env.elastic_root_index}-chunk-{int(time.time())}"

        for file in File.objects.exclude(status__in=File.INACTIVE_STATUSES):
            logger.debug("Reingesting file object %s", file)
            async_task(
                ingest,
                file.id,
                new_index,
                task_name=file.file_name,
                group="re-ingest",
                sync=kwargs["sync"],
            )
        async_task(switch_aliases, env.elastic_chunk_alias, new_index, task_name="switch_aliases")
