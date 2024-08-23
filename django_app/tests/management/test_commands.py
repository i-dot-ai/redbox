import re
import uuid
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from io import StringIO
from time import sleep
from unittest.mock import MagicMock, patch

import pytest
import requests
from botocore.exceptions import UnknownClientMethodError
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import CommandError, call_command
from django.utils import timezone
from freezegun import freeze_time
from magic_link.models import MagicLink
from requests_mock import Mocker

from redbox_app.redbox_core.models import Chat, ChatMessage, ChatRoleEnum, File, StatusEnum, User

# === check_file_status command tests ===


@patch("redbox_app.redbox_core.models.File.delete_from_s3")
@patch("redbox_app.redbox_core.models.File.original_file.field.storage.save")
@pytest.mark.django_db()
def test_check_file_status(deletion_mock: MagicMock, put_mock: MagicMock, alice: User, requests_mock: Mocker):
    # Based on: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3/client/delete_object.html
    deletion_mock.side_effect = {
        "DeleteMarker": True,
    }
    put_mock.side_effect = yield

    # Given
    def create_files():
        files = []

        for i in range(3):
            filename = f"original_file_{i}.txt"
            files.append(
                File.objects.create(
                    user=alice,
                    original_file=SimpleUploadedFile(filename, b"Lorem Ipsum."),
                    original_file_name=filename,
                    core_file_uuid=uuid.uuid4(),
                )
            )
        return files

    file_in_core_api, file_with_surprising_status, file_not_in_core_api, file_core_api_error = create_files()

    matcher = re.compile(f"http://{settings.CORE_API_HOST}:{settings.CORE_API_PORT}/file/[0-9a-f]|\\-/status")

    requests_mock.get(
        matcher,
        status_code=HTTPStatus.CREATED,
        json={
            "processing_status": StatusEnum.processing,
        },
    )
    requests_mock.get(
        f"http://{settings.CORE_API_HOST}:{settings.CORE_API_PORT}/file/{file_with_surprising_status.core_file_uuid}/status",
        status_code=HTTPStatus.CREATED,
        json={
            "processing_status": "this_is_a_surprising_string",
        },
    )
    requests_mock.get(
        f"http://{settings.CORE_API_HOST}:{settings.CORE_API_PORT}/file/{file_not_in_core_api.core_file_uuid}/status",
        status_code=HTTPStatus.NOT_FOUND,
    )
    requests_mock.get(
        f"http://{settings.CORE_API_HOST}:{settings.CORE_API_PORT}/file/{file_core_api_error.core_file_uuid}/status",
        exc=requests.exceptions.Timeout,
    )
    # When
    call_command("check_file_status")

    # Then
    assert File.objects.get(id=file_in_core_api.id).status == StatusEnum.processing
    assert File.objects.get(id=file_with_surprising_status.id).status == StatusEnum.processing
    assert File.objects.get(id=file_not_in_core_api.id).status == StatusEnum.deleted
    assert File.objects.get(id=file_core_api_error.id).status == StatusEnum.errored


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
def test_delete_expired_files(
    uploaded_file: File, requests_mock: Mocker, last_referenced: datetime, should_delete: bool
):
    # Given
    mock_file = uploaded_file
    mock_file.last_referenced = last_referenced
    mock_file.save()

    matcher = re.compile(f"http://{settings.CORE_API_HOST}:{settings.CORE_API_PORT}/file/[0-9a-f]|\\-")
    requests_mock.delete(
        matcher,
        status_code=HTTPStatus.CREATED,
        json={
            "key": mock_file.original_file_name,
            "bucket": settings.BUCKET_NAME,
            "uuid": str(uuid.uuid4()),
        },
    )

    # When
    call_command("delete_expired_data")

    # Then
    is_deleted = File.objects.get(id=mock_file.id).status == StatusEnum.deleted
    assert is_deleted == should_delete


@pytest.mark.django_db()
def test_delete_expired_files_with_api_error(uploaded_file: File, requests_mock: Mocker):
    # Given
    mock_file = uploaded_file
    mock_file.last_referenced = EXPIRED_FILE_DATE
    mock_file.save()

    matcher = re.compile(f"http://{settings.CORE_API_HOST}:{settings.CORE_API_PORT}/file/[0-9a-f]|\\-")

    requests_mock.delete(
        matcher,
        status_code=HTTPStatus.CREATED,
        json={
            "key": mock_file.original_file_name,
            "bucket": settings.BUCKET_NAME,
            "uuid": str(uuid.uuid4()),
        },
    )
    (
        requests_mock.delete(
            f"http://{settings.CORE_API_HOST}:{settings.CORE_API_PORT}/file/{mock_file.core_file_uuid}",
            exc=requests.exceptions.HTTPError,
        ),
    )

    # When
    call_command("delete_expired_data")

    # Then
    assert File.objects.get(id=mock_file.id).status == StatusEnum.errored


@patch("redbox_app.redbox_core.models.File.delete_from_s3")
@pytest.mark.django_db()
def test_delete_expired_files_with_s3_error(deletion_mock: MagicMock, uploaded_file: File, requests_mock: Mocker):
    deletion_mock.side_effect = UnknownClientMethodError(method_name="")

    # Given
    mock_file = uploaded_file
    mock_file.last_referenced = EXPIRED_FILE_DATE
    mock_file.save()

    matcher = re.compile(f"http://{settings.CORE_API_HOST}:{settings.CORE_API_PORT}/file/[0-9a-f]|\\-")

    requests_mock.delete(
        matcher,
        status_code=HTTPStatus.CREATED,
        json={
            "key": mock_file.original_file_name,
            "bucket": settings.BUCKET_NAME,
            "uuid": str(uuid.uuid4()),
        },
    )

    # When
    call_command("delete_expired_data")

    # Then
    assert File.objects.get(id=mock_file.id).status == StatusEnum.errored


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
        chat_message_1 = ChatMessage.objects.create(chat=test_chat, text="A question?", role=ChatRoleEnum.user)
    with freeze_time(msg_2_date):
        chat_message_2 = ChatMessage.objects.create(chat=test_chat, text="A question?", role=ChatRoleEnum.user)

    # When
    call_command("delete_expired_data")

    # Then
    assert Chat.objects.filter(id=chat.id).exists() != should_delete
    assert ChatMessage.objects.filter(id=chat_message_1.id).exists() != should_delete
    assert ChatMessage.objects.filter(id=chat_message_2.id).exists() != should_delete


# === reingest_files command tests ===


@pytest.mark.django_db(transaction=True)
def test_reingest_files(uploaded_file: File, requests_mock: Mocker, mocker):
    # Given
    assert uploaded_file.status == StatusEnum.processing

    requests_mock.post(
        f"http://{settings.UNSTRUCTURED_HOST}:8000/general/v0/general",
        json=[{"text": "hello", "metadata": {"filename": "my-file.txt"}}],
    )

    # When
    with mocker.patch("redbox.chains.ingest.VectorStore.aadd_documents", return_value=[]):
        call_command("reingest_files", sync=True)

    # Then
    for _ in range(5):
        uploaded_file.refresh_from_db()

        # Handle race condition from async reingestion
        if uploaded_file.status == StatusEnum.processing:
            sleep(1)
            continue

        assert uploaded_file.status == StatusEnum.complete


@pytest.mark.django_db(transaction=True)
def test_reingest_files_unstructured_fail(uploaded_file: File, requests_mock: Mocker, mocker):
    # Given
    assert uploaded_file.status == StatusEnum.processing

    requests_mock.post(
        f"http://{settings.UNSTRUCTURED_HOST}:8000/general/v0/general",
        json=[],
    )

    # When
    with mocker.patch("redbox.chains.ingest.VectorStore.aadd_documents", return_value=[]):
        call_command("reingest_files", sync=True)

    # Then
    for _ in range(5):
        uploaded_file.refresh_from_db()

        # Handle race condition from async reingestion
        if uploaded_file.status == StatusEnum.processing:
            sleep(1)
            continue

        assert uploaded_file.status == StatusEnum.errored
        assert uploaded_file.ingest_error == "Unstructured failed to extract text for this file"
