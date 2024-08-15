import logging

from django.core.management import BaseCommand
from django_q.models import Schedule
from django_q.tasks import schedule

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *_args, **_kwargs):
        self.stdout.write(self.style.NOTICE("Adding delete expired data task to Queue"))

        # create the task
        schedule(
            "django.core.management.call_command", "delete_expired_data", schedule_type=Schedule.CRON, cron="50 * * * *"
        )
