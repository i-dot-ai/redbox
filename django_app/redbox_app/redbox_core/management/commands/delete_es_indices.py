import logging

from django.core.management import BaseCommand

from redbox.models import Settings

logger = logging.getLogger(__name__)

env = Settings()

es_client = env.elasticsearch_client()


class Command(BaseCommand):
    help = """
    This is a command to remove old ElasticSearch indexes after reingestion and realiasing.
    Eventually, this may be combined into reingest_files,
    but this allows for a manual check of data before deletion.

    The new_index should be available as an arg on the recent redbox_app.worker.ingest tasks in Django Admin.
    """

    def add_arguments(self, parser):
        parser.add_argument("new_index", nargs="?", type=str)

    def list_chunk_indices(self):
        try:
            # Get all indices
            indices = es_client.cat.indices(format="json")
            # Filter indices that contain '-chunk'
            return [index["index"] for index in indices if "-chunk" in index["index"]]
        except Exception as e:
            logger.exception("Error fetching indices", exc_info=e)

    def handle(self, *_args, **kwargs):
        chunk_indices = self.list_chunk_indices()

        for index in chunk_indices:
            if index != kwargs["new_index"]:
                es_client.indices.delete(index=index)
