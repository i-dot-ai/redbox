from django.core.management import BaseCommand

from redbox.models.settings import get_settings

env = get_settings()

es_client = env.elasticsearch_client()


class Command(BaseCommand):
    help = """This is a one-off command to add an ElasticSearch alias to the existing chunks index."""

    def handle(self, *args, **kwargs):  # noqa:ARG002
        existing_index = f"{env.elastic_root_index}-chunk"
        self.stdout.write(self.style.NOTICE(f"Creating the alias {existing_index}-current"))

        if not es_client.indices.exists_alias(name=f"{existing_index}-current"):
            es_client.indices.put_alias(index=existing_index, name=f"{existing_index}-current")
