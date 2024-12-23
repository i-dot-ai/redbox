import logging
from uuid import UUID

from redbox.loader.ingester import ingest_file, simple_ingest
from redbox.models.settings import get_settings

env = get_settings()


def ingest(file_id: UUID) -> None:
    # These models need to be loaded at runtime otherwise they can be loaded before they exist
    from redbox_app.redbox_core.models import File

    file = File.objects.get(id=file_id)

    logging.info("Ingesting file: %s", file)

    try:
        file.text, file.metadata = simple_ingest(file.unique_name)
        file.status = File.Status.complete
        file.save()
    except Exception as error:
        file.status = File.Status.errored
        file.ingest_error = error
        file.save()


