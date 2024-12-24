import json
import logging
from uuid import UUID

from redbox.loader.ingester import ingest_file


def ingest(file_id: UUID) -> None:
    # These models need to be loaded at runtime otherwise they can be loaded before they exist
    from redbox_app.redbox_core.models import File

    file = File.objects.get(id=file_id)

    logging.info("Ingesting file: %s", file)

    try:
        text, metadata = ingest_file(file.unique_name)
        file.text, file.metadata = text, json.loads(metadata.model_dump_json())
        file.status = File.Status.complete
        file.save()
    except Exception as error:  # noqa: BLE001
        file.status = File.Status.errored
        file.ingest_error = str(error)
        file.save()
