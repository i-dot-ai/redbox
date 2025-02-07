from datetime import UTC, datetime, timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from freezegun import freeze_time
from lxml.html.diff import token
from pytz import utc

from redbox_app.redbox_core.models import (
    ChatMessage,
    File,
)


@pytest.mark.django_db()
def test_file_model_last_referenced(chat, s3_client):  # noqa: ARG001
    mock_file = SimpleUploadedFile("test.txt", b"these are the file contents")

    new_file = File.objects.create(status=File.Status.processing, original_file=mock_file, chat=chat)

    # Tests the initial value of the last_referenced
    expected_last_referenced = new_file.created_at
    # The last_referenced should be FILE_EXPIRY_IN_SECONDS ahead of created_at
    # these fields are set during the same save() process
    # this test accounts for a delay between creating the fields
    assert abs(new_file.last_referenced - expected_last_referenced) < timedelta(seconds=1)

    # Tests that the last_referenced field can be updated
    new_date = datetime(2028, 1, 1, tzinfo=UTC)
    new_file.last_referenced = new_date
    new_file.save()
    assert new_file.last_referenced == new_date


@pytest.mark.django_db()
def test_chat_message_model_token_count_on_save(chat):
    chat_message = ChatMessage(chat=chat, role=ChatMessage.Role.ai, text="I am a message")
    assert not chat_message.token_count
    chat_message.save()
    assert chat_message.token_count == 4


@pytest.mark.django_db()
@pytest.mark.parametrize("role, expected_count", [(ChatMessage.Role.ai, 0), (ChatMessage.Role.user, 100)])
def test_associated_file_token_count(chat, original_file, role, expected_count):

    now = datetime.now(tz=utc)

    # Given a chat message...
    with freeze_time(now):
        chat_message = ChatMessage.objects.create(chat=chat, role=role, text="I am a message")

    # and a file created before it...
    with freeze_time(now - timedelta(seconds=1)):
        File.objects.create(original_file=original_file, chat=chat, token_count=100)


    # and a file created after it...
    with freeze_time(now + timedelta(seconds=1)):
        File.objects.create(original_file=original_file, chat=chat, token_count=200)

    # when i call associated_file_token_count
    # I expect to see the token count for the file created before it in the count
    assert chat_message.associated_file_token_count == expected_count
