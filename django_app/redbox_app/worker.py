import logging
from uuid import UUID

from django.conf import settings

from redbox.loader.ingester import ingest_file
from redbox.models import File as CoreFile
from redbox.models import ProcessingStatusEnum


async def ingest(file_id: UUID):
    # These models need to be loaded at runtime otherwise they can be loaded before they exist
    from redbox_app.redbox_core.models import File, StatusEnum

    file = File.objects.get(id=file_id)

    logging.info("Ingesting file: %s", file)

    core_file = CoreFile(
        key=file.unique_name,
        bucket=settings.BUCKET_NAME,
        creator_user_uuid=file.user.id,
        uuid=file.core_file_uuid,
    )
    core_file.ingest_status = ProcessingStatusEnum.embedding

    error = await ingest_file(core_file)

    if error:
        file.status = StatusEnum.errored
        file.ingest_error = error
    else:
        file.status = StatusEnum.complete

    file.save()
