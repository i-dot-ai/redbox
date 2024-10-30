import json
import logging
import os
from datetime import timedelta

import requests
from botocore.exceptions import BotoCoreError
from django.conf import settings
from django.core.management import BaseCommand
from django.db.models import Max
from django.utils import timezone
from requests.exceptions import RequestException

from redbox_app.redbox_core.models import Chat, File

logger = logging.getLogger(__name__)


def post_summary_to_slack(message):
    slack_url = os.environ.get("SLACK_NOTIFICATION_URL", None)
    if slack_url:
        try:
            r = requests.post(
                slack_url,
                data=json.dumps({"text": message}),
                timeout=60,
                headers={"Content-Type": "application/json"},
            )

            r.raise_for_status()

        except RequestException:
            logger.exception("Error trying to communicate with Slack")
    else:
        logger.info("The slack url for the feedback hook was not provided")


class Command(BaseCommand):
    help = """This should be run daily per environment to remove expired data.
    It removes Files, ChatMessages and ChatHistories that have exceeded their expiry date.
    """

    def handle(self, *_args, **_kwargs):
        try:
            cutoff_date = timezone.now() - timedelta(seconds=settings.FILE_EXPIRY_IN_SECONDS)

            self.stdout.write(self.style.NOTICE(f"Deleting Files expired before {cutoff_date}"))
            counter = 0
            failure_counter = 0

            for file in File.objects.filter(last_referenced__lt=cutoff_date).exclude(status__in=File.INACTIVE_STATUSES):
                logger.debug(
                    "Deleting file object %s, last_referenced %s",
                    file,
                    file.last_referenced,
                )

                try:
                    file.delete_from_elastic()
                    file.delete_from_s3()

                except BotoCoreError as e:
                    logger.exception("Error deleting file object %s from storage", file, exc_info=e)
                    file.status = File.Status.errored
                    file.save()
                    failure_counter += 1
                except Exception as e:
                    logger.exception("Error deleting file object %s", file, exc_info=e)
                    file.status = File.Status.errored
                    file.save()
                    failure_counter += 1
                else:
                    file.status = File.Status.deleted
                    file.save()
                    logger.debug("File object %s deleted", file)

                    counter += 1

            self.stdout.write(self.style.SUCCESS(f"Successfully deleted {counter} file objects"))

            self.stdout.write(self.style.NOTICE(f"Deleting chats expired before {cutoff_date}"))
            chats_to_delete = Chat.objects.annotate(last_modified_at=Max("chatmessage__modified_at")).filter(
                last_modified_at__lt=cutoff_date
            )
            chat_counter = chats_to_delete.count()
            chats_to_delete.delete()

            self.stdout.write(self.style.SUCCESS(f"Successfully deleted {chat_counter} ChatHistory objects"))
            post_summary_to_slack(
                f"The file deletion task succeeded in {os.environ["ENVIRONMENT"]} :put_litter_in_its_place:. {counter} "
                f"files deleted. {chat_counter} chats deleted. {failure_counter} failures."
            )
        except Exception:  # noqa: BLE001 - ignore catchall exception
            post_summary_to_slack("The file deletion task failed :do_not_litter:")
