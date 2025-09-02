import contextlib
import json
from datetime import datetime, timedelta

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone
from freezegun import freeze_time
from pytz import utc

from redbox_app.redbox_core.models import Chat, ChatMessage, File

User = get_user_model()


# === delete_expired_data command tests ===
EXPIRED_FILE_DATE = timezone.now() - timedelta(seconds=(settings.FILE_EXPIRY_IN_SECONDS + 60))


@pytest.mark.parametrize(
    ("last_referenced", "should_delete"),
    [
        (EXPIRED_FILE_DATE, True),
        (timezone.now(), False),
    ],
)
@pytest.mark.django_db()
def test_delete_expired_files(uploaded_file: File, last_referenced: datetime, should_delete: bool):
    # Given
    mock_file = uploaded_file
    mock_file.last_referenced = last_referenced
    mock_file.save()

    # When
    call_command("delete_expired_data")

    # Then
    is_deleted = not File.objects.filter(id=mock_file.id).exists()
    assert is_deleted == should_delete


@pytest.mark.django_db()
def test_delete_expired_files_with_s3_error(uploaded_file: File):
    # Given
    mock_file = uploaded_file
    mock_file.last_referenced = EXPIRED_FILE_DATE
    mock_file.save()

    # When
    call_command("delete_expired_data")

    # Then
    assert not File.objects.filter(id=mock_file.id).exists()


@pytest.mark.parametrize(
    ("msg_1_date", "msg_2_date", "should_delete"),
    [
        (EXPIRED_FILE_DATE, EXPIRED_FILE_DATE, True),
        (EXPIRED_FILE_DATE, timezone.now(), False),
        (timezone.now(), timezone.now(), False),
    ],
)
@pytest.mark.django_db()
def test_delete_expired_chats(chat: Chat, msg_1_date: datetime, msg_2_date: datetime, should_delete: bool):
    # Given
    test_chat = chat
    with freeze_time(msg_1_date):
        chat_message_1 = ChatMessage.objects.create(
            chat=test_chat,
            text="A question?",
            role=ChatMessage.Role.user,
        )
    with freeze_time(msg_2_date):
        chat_message_2 = ChatMessage.objects.create(
            chat=test_chat,
            text="A question?",
            role=ChatMessage.Role.user,
        )

    # When
    call_command("delete_expired_data")

    # Then
    assert Chat.objects.filter(id=chat.id).exists() != should_delete
    assert ChatMessage.objects.filter(id=chat_message_1.id).exists() != should_delete
    assert ChatMessage.objects.filter(id=chat_message_2.id).exists() != should_delete


# === reingest_files command tests ===


@pytest.mark.django_db(transaction=True)
def test_reingest_files(uploaded_file: File):
    # Given
    assert uploaded_file.status == File.Status.processing

    # When
    call_command("reingest_files", sync=True)

    # Then
    uploaded_file.refresh_from_db()
    assert uploaded_file.status == File.Status.complete


@pytest.mark.django_db(transaction=True)
def test_chat_metrics(user_with_chats_with_messages_over_time: Chat, s3_client):  # noqa: ARG001
    # delete file if it already exists
    try:
        s3_client.delete_object(Bucket=settings.BUCKET_NAME, Key=settings.METRICS_FILE_NAME)
    except Exception:  # noqa: BLE001
        contextlib.suppress(Exception)

    # When
    call_command("chat_metrics")

    def read_line(txt):
        return json.loads(f"[{txt.decode()}]")

    # Then
    lines = list(
        map(
            read_line,
            s3_client.get_object(Bucket=settings.BUCKET_NAME, Key=settings.METRICS_FILE_NAME)["Body"].readlines(),
        )
    )

    def historic_date(days_ago: int):
        return (datetime.now(tz=utc) - timedelta(days=days_ago)).strftime("%Y-%m-%d")

    expected_value = [
        [
            "extraction_date",
            "created_at__date",
            "department",
            "business_unit",
            "grade",
            "profession",
            "ai_experience",
            "token_count__avg",
            "rating__avg",
            "delay__avg",
            "id__count",
            "n_selected_files__count",
            "chat_id__count",
            "user_id__count",
        ],
        [
            historic_date(days_ago=0),
            historic_date(days_ago=40),
            "Cabinet Office",
            "Government Business Services",
            "D",
            "IA",
            "Experienced Navigator",
            3.0,
            None,
            0.0,
            1,
            0.0,
            1,
            1,
        ],
        [
            historic_date(days_ago=0),
            historic_date(days_ago=20),
            "Cabinet Office",
            "Government Business Services",
            "D",
            "IA",
            "Experienced Navigator",
            3.0,
            None,
            0.0,
            1,
            0.0,
            1,
            1,
        ],
        [
            historic_date(days_ago=0),
            historic_date(days_ago=5),
            "Cabinet Office",
            "Government Business Services",
            "D",
            "IA",
            "Experienced Navigator",
            3.0,
            None,
            0.0,
            1,
            0.0,
            1,
            1,
        ],
        [
            historic_date(days_ago=0),
            historic_date(days_ago=1),
            "Cabinet Office",
            "Government Business Services",
            "D",
            "IA",
            "Experienced Navigator",
            2.0,
            None,
            0.0,
            1,
            0.0,
            1,
            1,
        ],
        [
            historic_date(days_ago=0),
            historic_date(days_ago=0),
            "Cabinet Office",
            "Government Business Services",
            "D",
            "IA",
            "Experienced Navigator",
            1.0,
            None,
            0.0,
            1,
            0.0,
            1,
            1,
        ],
    ]
    assert lines == expected_value
