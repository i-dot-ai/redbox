import logging
from uuid import UUID

from redbox.loader.ingester import ingest_file
from redbox.models.settings import get_settings

env = get_settings()


def ingest(file_id: UUID, es_index: str | None = None) -> None:
    # These models need to be loaded at runtime otherwise they can be loaded before they exist
    from redbox_app.redbox_core.models import File

    if not es_index:
        es_index = env.elastic_chunk_alias

    file = File.objects.get(id=file_id)

    logging.info("Ingesting file: %s", file)

    if error := ingest_file(file.unique_name, es_index):
        file.status = File.Status.errored
        file.ingest_error = error
    else:
        file.status = File.Status.complete

    file.save()
