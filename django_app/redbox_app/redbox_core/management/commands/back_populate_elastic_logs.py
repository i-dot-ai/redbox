from django.core.management import BaseCommand

from redbox_app.redbox_core.models import ChatMessage, User


class Command(BaseCommand):
    help = """This is a one-off command to back populate elastic logs."""

    def add_arguments(self, parser):
        parser.add_argument("model", nargs="?", type=str, default="chat_message")

    def handle(self, *args, **kwargs):  # noqa:ARG002
        model_name = kwargs["model"]
        model_map = {"chat_message": ChatMessage, "user": User}
        if model_name not in model_map:
            msg = f"{model_name} not recognised"
            raise ValueError(msg)

        for chat_message in model_map[model_name].objects.all():
            chat_message.log()
