import json
import os
from datetime import UTC, datetime, timedelta
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import elasticsearch
import pytest
from botocore.exceptions import UnknownClientMethodError
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import CommandError, call_command
from django.utils import timezone
from freezegun import freeze_time
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from magic_link.models import MagicLink
from pytest_mock import MockerFixture
from requests_mock import Mocker

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
    is_deleted = File.objects.get(id=mock_file.id).status == File.Status.deleted
    assert is_deleted == should_delete


@patch("redbox_app.redbox_core.models.File.delete_from_elastic")
@pytest.mark.django_db()
def test_delete_expired_files_with_elastic_error(deletion_mock: MagicMock, uploaded_file: File):
    deletion_mock.side_effect = elasticsearch.BadRequestError(message="i am am error", meta=None, body=None)

    # Given
    mock_file = uploaded_file
    mock_file.last_referenced = EXPIRED_FILE_DATE
    mock_file.save()

    # When
    call_command("delete_expired_data")

    # Then
    assert File.objects.get(id=mock_file.id).status == File.Status.errored


@patch("redbox_app.redbox_core.models.File.delete_from_s3")
@pytest.mark.django_db()
def test_delete_expired_files_with_s3_error(deletion_mock: MagicMock, uploaded_file: File):
    deletion_mock.side_effect = UnknownClientMethodError(method_name="")

    # Given
    mock_file = uploaded_file
    mock_file.last_referenced = EXPIRED_FILE_DATE
    mock_file.save()

    # When
    call_command("delete_expired_data")

    # Then
    assert File.objects.get(id=mock_file.id).status == File.Status.errored


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
def test_reingest_files(uploaded_file: File, requests_mock: Mocker, mocker: MockerFixture):
    # Given
    assert uploaded_file.status == File.Status.processing

    requests_mock.post(
        f"http://{settings.UNSTRUCTURED_HOST}:8000/general/v0/general",
        json=[{"text": "hello", "metadata": {"filename": "my-file.txt"}}],
    )

    # When
    mocker.patch("redbox.chains.ingest.VectorStore.add_documents", return_value=[])
    mocker.patch(
        "redbox.loader.loaders.get_chat_llm",
        return_value=GenericFakeChatModel(
            messages=iter(
                [
                    json.dumps(
                        {
                            "name": "foo",
                            "description": "more test",
                            "keywords": ["hello", "world"],
                        }
                    )
                ]
            )
        ),
    )

    call_command("reingest_files", sync=True)

    # Then
    uploaded_file.refresh_from_db()
    assert uploaded_file.status == File.Status.complete


@pytest.mark.django_db(transaction=True)
def test_reingest_files_unstructured_fail(uploaded_file: File, requests_mock: Mocker, mocker):
    # Given
    assert uploaded_file.status == File.Status.processing

    requests_mock.post(
        f"http://{settings.UNSTRUCTURED_HOST}:8000/general/v0/general",
        json=[],
    )

    mocker.patch(
        "redbox.loader.loaders.get_chat_llm",
        return_value=GenericFakeChatModel(
            messages=iter(
                [
                    json.dumps(
                        {
                            "name": "foo",
                            "description": "more test",
                            "keywords": ["hello", "world"],
                        }
                    )
                ]
            )
        ),
    )

    # When
    with mocker.patch("redbox.chains.ingest.VectorStore.add_documents", return_value=[]):
        call_command("reingest_files", sync=True)

    # Then
    uploaded_file.refresh_from_db()
    assert uploaded_file.status == File.Status.errored
    assert uploaded_file.ingest_error == "<class 'ValueError'>: Unstructured failed to extract text for this file"


def test_delete_es_indices_no_new_index():
    # Given

    # When
    with pytest.raises(CommandError) as exception:
        call_command("delete_es_indices")

    # Then
    assert str(exception.value) == "No new index given for alias"


@pytest.mark.django_db(transaction=True)
def test_update_users(alice: User):
    original_file_path = os.path.join(  # noqa: PTH118
        os.path.dirname(os.path.abspath(__file__)),  # noqa: PTH100, PTH120
        "..",
        "data/csv/user_update.json",
    )

    original_file = SimpleUploadedFile(
        "user_update.json",
        Path.open(original_file_path, "rb").read(),
    )
    file = File.objects.create(
        user=alice,
        original_file=original_file,
        last_referenced=datetime.now(tz=UTC) - timedelta(days=14),
        status=File.Status.processing,
    )
    file.save()

    assert not alice.usage_at_work
    assert not User.objects.filter(email="bob@cabinetoffice.gov.uk").exists()

    call_command("update_users", file.id)
    alice.refresh_from_db()

    assert alice.usage_at_work == "Everyday"
    assert User.objects.filter(email="bob@cabinetoffice.gov.uk").exists()

    bob = User.objects.get(email="bob@cabinetoffice.gov.uk")
    assert bob.usage_at_work == "Monthly or a few times per month"
