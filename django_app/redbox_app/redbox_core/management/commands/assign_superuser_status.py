from django.core.management import BaseCommand
from django_otp.plugins.otp_totp.models import TOTPDevice
from redbox_app.redbox_core.models import User


class Command(BaseCommand):
    help = """This should be run once per environment to set the initial superuser.
    Thereafter the superuser should assign new staff users via the admin and send
    them the link to the Authenticator.

    Once run this command will return the link to a Time-One-Time-Pass that the
    superuser should use to enable login to the admin portal."""

    def add_arguments(self, parser):
        parser.add_argument(
            "-e", "--email", type=str, help="user's email", required=True
        )
        parser.add_argument("-p", "--password", type=str, help="user's new password")

    def handle(self, *args, **kwargs):
        email = kwargs["email"]
        password = kwargs["password"]

        user, _ = User.objects.get_or_create(email=email)

        user.is_superuser = True
        user.is_staff = True
        if password:
            user.set_password(password)

        user.save()
        user.refresh_from_db()

        if not user.password:
            self.stderr.write(
                self.style.ERROR(f"A password must be set for '{email}'.")
            )
            return

        device, _ = TOTPDevice.objects.get_or_create(
            user=user, confirmed=True, tolerance=0
        )
        self.stdout.write(device.config_url)
        return
