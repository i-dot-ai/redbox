import logging
from datetime import timedelta

from botocore.exceptions import BotoCoreError
from django.conf import settings
from django.core.management import BaseCommand
from django.utils import timezone
from redbox_app.redbox_core.client import CoreApiClient
from redbox_app.redbox_core.models import File, StatusEnum
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)
core_api = CoreApiClient(host=settings.CORE_API_HOST, port=settings.CORE_API_PORT)


class Command(BaseCommand):
    help = """This should be run daily per environment to remove expired data.
    It removes Files that have exceeded their expiry date.
    """

    def handle(self, *_args, **_kwargs):
        cutoff_date = timezone.now() - timedelta(seconds=settings.FILE_EXPIRY_IN_SECONDS)

        self.stdout.write(self.style.NOTICE(f"Deleting Files expired before {cutoff_date}"))
        counter = 0

        for file in File.objects.filter(last_referenced__lt=cutoff_date):
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
            except BotoCoreError as e:
                logger.exception("Error deleting file object %s from storage", file, exc_info=e)
            else:
                file.status = StatusEnum.deleted
                file.save()
                logger.debug("File object %s deleted", file)

                counter += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully deleted {counter} file objects"))
