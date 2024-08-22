import logging

from django.conf import settings

from redbox.loader.ingester import ingest_file
from redbox.models import File as CoreFile
from redbox.models import ProcessingStatusEnum


def ingest(file):
    # These models need to be loaded at runtime otherwise they can be loaded before they exist
    from redbox_app.redbox_core.models import StatusEnum

    logging.info("Ingesting file: %s", file)

    core_file = CoreFile(
        key=file.unique_name,
        bucket=settings.BUCKET_NAME,
        creator_user_uuid=file.user.id,
        uuid=file.core_file_uuid,
    )
    core_file.ingest_status = ProcessingStatusEnum.embedding
    if error := ingest_file(core_file):
        core_file.ingest_status = ProcessingStatusEnum.failed
    else:
        file.ingest_error = error
        file.status = StatusEnum.errored

    file.save()
