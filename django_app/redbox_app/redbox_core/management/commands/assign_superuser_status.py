import logging

from django.conf import settings
from django.core.management import BaseCommand
from redbox_app.redbox_core.models import User

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class Command(BaseCommand):
    help = """This should be run once per environment to set the initial superuser.
    Thereafter the superuser should be able to login and assign new staff users via the admin.
    """

    def handle(self, *args, **kwargs):
        if email := settings.SUPERUSER_EMAIL:
            user, created = User.objects.get_or_create(email=email)
            user.is_superuser = True
            user.is_staff = True
            user.save()
            user.refresh_from_db()
            if created:
                logger.info("created superuser")
            return
