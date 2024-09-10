import logging
from uuid import UUID

from redbox.loader.ingester import ingest_file


def ingest(file_id: UUID):
    # These models need to be loaded at runtime otherwise they can be loaded before they exist
    from redbox_app.redbox_core.models import File, StatusEnum

    file = File.objects.get(id=file_id)

    logging.info("Ingesting file: %s", file)

    if error := ingest_file(file.unique_name):
        file.status = StatusEnum.errored
        file.ingest_error = error
    else:
        file.status = StatusEnum.complete

    file.save()
