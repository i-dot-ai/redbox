import logging

from django.core.management import BaseCommand

from redbox.models.settings import get_settings

logger = logging.getLogger(__name__)

env = get_settings()

es_client = env.elasticsearch_client()


class Command(BaseCommand):
    help = """
    This is a command to change the aliased elasticsearch index after a reingestion.
    Eventually, this may be able to be combined into reingest_files,
    but this allows for a manual check of reingestion before moving the alias.

    The new_index should be available as an arg on the recent redbox_app.worker.ingest tasks in Django Admin.
    """

    def add_arguments(self, parser):
        default_alias = env.elastic_chunk_alias

        parser.add_argument("new_index", nargs="?", type=str)
        parser.add_argument("alias", nargs="?", type=str, default=default_alias)

    def handle(self, *_args, **kwargs):
        try:
            response = es_client.indices.get_alias(name=kwargs["alias"])
            indices_to_remove = list(response)
        except Exception as e:
            logger.exception("Error fetching alias", exc_info=e)

        actions = [{"remove": {"index": index, "alias": kwargs["alias"]}} for index in indices_to_remove]
        actions.append({"add": {"index": kwargs["new_index"], "alias": kwargs["alias"]}})

        es_client.indices.update_aliases(body={"actions": actions})
