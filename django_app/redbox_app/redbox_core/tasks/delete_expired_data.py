import logging
from datetime import timedelta

from botocore.exceptions import BotoCoreError
from django.conf import settings
from django.db.models import Max
from django.utils import timezone
from requests.exceptions import RequestException

from redbox_app.redbox_core.client import CoreApiClient
from redbox_app.redbox_core.models import ChatHistory, File, StatusEnum

logger = logging.getLogger(__name__)
core_api = CoreApiClient(host=settings.CORE_API_HOST, port=settings.CORE_API_PORT)

statuses_to_exclude = [StatusEnum.deleted, StatusEnum.errored]


def task():
    cutoff_date = timezone.now() - timedelta(seconds=settings.FILE_EXPIRY_IN_SECONDS)

    logger.info("Deleting Files expired before %s", cutoff_date)
    file_counter = 0
    errored_files = []

    for file in File.objects.filter(last_referenced__lt=cutoff_date).exclude(status__in=statuses_to_exclude):
        logger.debug(
            "Deleting file object %s, last_referenced %s",
            file,
            file.last_referenced,
        )

        try:
            core_api.delete_file(file.core_file_uuid, file.user)
            file.delete_from_s3()

        except RequestException as e:
            logger.exception("Error deleting file object %s using core-api", file, exc_info=e)
            file.status = StatusEnum.errored
            file.save()
            errored_files.append(file)
        except BotoCoreError as e:
            logger.exception("Error deleting file object %s from storage", file, exc_info=e)
            file.status = StatusEnum.errored
            file.save()
            errored_files.append(file.id)
        else:
            file.status = StatusEnum.deleted
            file.save()
            logger.debug("File object %s deleted", file)

            file_counter += 1

    logger.info("Successfully deleted %s file objects", file_counter)

    logger.info("Deleting chats expired before %s", cutoff_date)
    chats_to_delete = ChatHistory.objects.annotate(last_modified_at=Max("chatmessage__modified_at")).filter(
        last_modified_at__lt=cutoff_date
    )
    chat_counter = chats_to_delete.count()
    chats_to_delete.delete()

    logger.info("Successfully deleted %s ChatHistory objects", chat_counter)

    return {"files_deleted": file_counter, "chats_deleted": chat_counter, "errored_files": errored_files}
