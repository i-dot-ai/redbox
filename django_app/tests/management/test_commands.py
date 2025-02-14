from datetime import UTC, datetime, timedelta
from io import StringIO

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.utils import timezone
from freezegun import freeze_time
from magic_link.models import MagicLink

from redbox_app.redbox_core.models import Chat, ChatMessage, File

User = get_user_model()


# === check_file_status command tests ===


# === show_magiclink_url command tests ===


@pytest.mark.django_db()
def test_command_output_no_such_user():
    # Given

    # When
    with pytest.raises(CommandError) as exception:
        call_command("show_magiclink_url", "alice@example.com")

    # Then
    assert str(exception.value) == "No User found with email alice@example.com"


@pytest.mark.django_db()
def test_command_output_no_links_ever(alice: User):
    # Given

    # When
    with pytest.raises(CommandError) as exception:
        call_command("show_magiclink_url", alice.email)

    # Then
    assert str(exception.value) == f"No MagicLink found for user {alice.email}"


@pytest.mark.django_db()
def test_command_output_no_valid_links(alice: User):
    # Given
    MagicLink.objects.create(user=alice, expires_at=datetime.now(UTC) - timedelta(seconds=10))

    # When
    with pytest.raises(CommandError) as exception:
        call_command("show_magiclink_url", alice.email)

    # Then
    assert str(exception.value) == f"No active link for user {alice.email}"


@pytest.mark.django_db()
def test_command_output_with_valid_links(alice: User):
    # Given
    link: MagicLink = MagicLink.objects.create(user=alice, expires_at=datetime.now(UTC) + timedelta(seconds=10))
    out, err = StringIO(), StringIO()

    # When
    call_command("show_magiclink_url", alice.email, stdout=out, stderr=err)

    # Then
    assert out.getvalue().strip() == link.get_absolute_url()


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
    assert s3_client.list_objects(Bucket=settings.BUCKET_NAME)

    # When
    call_command("chat_metrics")

    # Then
    assert s3_client.get_object(Bucket=settings.BUCKET_NAME, Key="metrics.csv")
