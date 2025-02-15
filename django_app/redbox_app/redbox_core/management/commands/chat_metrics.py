import json
from pathlib import Path

from django.conf import settings
from django.core.management import BaseCommand
from rest_framework.fields import CharField, DateField, FloatField, IntegerField
from rest_framework.serializers import Serializer

from redbox.models import Settings
from redbox_app.redbox_core.models import ChatMessage

env = Settings()
s3_client = env.s3_client()


def to_csv(writer, record):
    writer.write(json.dumps(list(record))[1:-1] + "\n")


class MetricSerializer(Serializer):
    created_at__date = DateField()
    business_unit = CharField(source="chat__user__business_unit")
    grade = CharField(source="chat__user__grade")
    profession = CharField(source="chat__user__profession")
    ai_experience = CharField(source="chat__user__ai_experience")
    token_count__avg = FloatField()
    rating__avg = FloatField()
    delay__avg = FloatField()
    id__count = IntegerField()
    n_selected_files__count = FloatField()
    chat_id__count = IntegerField()
    user_id__count = IntegerField()


class Command(BaseCommand):
    help = """dump metrics as csv to s3"""

    def handle(self, *args, **kwargs):  # noqa: ARG002
        serializer = MetricSerializer(ChatMessage.metrics().all(), many=True)
        file_name = "metrics.csv"
        local_file_path = Path.home() / "metrics.csv"
        with Path.open(local_file_path, "w") as f:
            if serializer.data:
                to_csv(f, serializer.data[0])
            for record in serializer.data:
                to_csv(f, record.values())

        s3_client.upload_file(local_file_path, settings.BUCKET_NAME, file_name)
