import json
from pathlib import Path

from django.core.management import BaseCommand
from rest_framework.fields import CharField, FloatField, IntegerField
from rest_framework.serializers import Serializer

from redbox.models import Settings
from redbox_app.redbox_core.models import ChatMessage

env = Settings()
s3_client = env.s3_client()


def to_csv(writer, record):
    writer.write(json.dumps(list(record))[1:-1] + "\n")


class MetricSerializer(Serializer):
    business_unit = CharField(source="chat__user__business_unit")
    grade = CharField(source="chat__user__grade")
    profession = CharField(source="chat__user__profession")
    ai_experience = CharField(source="chat__user__ai_experience")

    token_count = FloatField(source="token_count__avg")
    rating = FloatField(source="rating__avg")
    delay_seconds = FloatField(source="delay__avg")
    id = IntegerField(source="id__count")
    n_selected_files = FloatField(source="n_selected_files__count")
    chat_id = IntegerField(source="chat_id__count")
    user_id = IntegerField(source="user_id__count")


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

        s3_client.upload_file(local_file_path, env.bucket_name, file_name)
