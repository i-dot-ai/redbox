from datetime import UTC, datetime, timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from yarl import URL

from redbox_app.redbox_core.models import (
    ChatMessage,
    Citation,
    File,
    InactiveFileError,
    User,
)


@pytest.mark.django_db()
def test_file_model_last_referenced(peter_rabbit, s3_client):  # noqa: ARG001
    mock_file = SimpleUploadedFile("test.txt", b"these are the file contents")

    new_file = File.objects.create(
        status=File.Status.processing,
        original_file=mock_file,
        user=peter_rabbit,
    )

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


@pytest.mark.parametrize(
    ("status"),
    [
        File.Status.complete,
        File.Status.processing,
    ],
)
@pytest.mark.django_db()
def test_file_model_unique_name(status: str, peter_rabbit: User, s3_client):  # noqa: ARG001
    mock_file = SimpleUploadedFile("test.txt", b"these are the file contents")

    new_file = File.objects.create(
        status=status,
        original_file=mock_file,
        user=peter_rabbit,
    )

    assert new_file.unique_name  # Check new name can be retrieved without error


@pytest.mark.parametrize(
    ("status"),
    [
        File.Status.deleted,
        File.Status.errored,
    ],
)
@pytest.mark.django_db()
def test_file_model_unique_name_error_states(status: str, peter_rabbit: User, s3_client):  # noqa: ARG001
    mock_file = SimpleUploadedFile("test.txt", b"these are the file contents")

    new_file = File.objects.create(
        status=status,
        original_file=mock_file,
        user=peter_rabbit,
    )

    with pytest.raises(InactiveFileError, match="is inactive, status is"):
        assert new_file.unique_name


@pytest.mark.django_db()
@pytest.mark.parametrize(
    ("source", "error_msg"),
    [
        (Citation.Origin.USER_UPLOADED_DOCUMENT, "file must be specified for a user-uploaded-document"),
        (Citation.Origin.WIKIPEDIA, "url must be specified for an external citation"),
    ],
)
def test_citation_save_fail_file_url_not_set(chat_message: ChatMessage, source, error_msg):
    citation = Citation(chat_message=chat_message, text="hello", source=source)

    with pytest.raises(ValueError, match=error_msg):
        citation.save()


@pytest.mark.django_db()
@pytest.mark.parametrize(
    ("source", "error_msg"),
    [
        (Citation.Origin.USER_UPLOADED_DOCUMENT, "url should not be specified for a user-uploaded-document"),
        (Citation.Origin.WIKIPEDIA, "file should not be specified for an external citation"),
    ],
)
def test_citation_save_fail_file_and_url_set(chat_message: ChatMessage, uploaded_file: File, source, error_msg):
    citation = Citation(
        chat_message=chat_message,
        text="hello",
        source=source,
        url="http://example.com",
        file=uploaded_file,
    )

    with pytest.raises(ValueError, match=error_msg):
        citation.save()


def test_internal_citation_uri(chat_message: ChatMessage, uploaded_file: File):
    citation = Citation(
        chat_message=chat_message,
        text="hello",
        source=Citation.Origin.USER_UPLOADED_DOCUMENT,
        file=uploaded_file,
    )
    citation.save()
    assert citation.uri.parts[-1] == "original_file.txt"


def test_external_citation_uri(
    chat_message: ChatMessage,
):
    citation = Citation(
        chat_message=chat_message,
        text="hello",
        source=Citation.Origin.WIKIPEDIA,
        url="http://example.com",
    )
    citation.save()
    assert citation.uri == URL("http://example.com")


def test_unique_citation_uris(chat_message: ChatMessage, uploaded_file: File):
    external_citation = Citation(
        chat_message=chat_message,
        text="hello",
        source=Citation.Origin.WIKIPEDIA,
        url="http://example.com",
    )
    external_citation.save()

    internal_citation = Citation(
        chat_message=chat_message,
        text="hello",
        source=Citation.Origin.USER_UPLOADED_DOCUMENT,
        file=uploaded_file,
    )
    internal_citation.save()

    chat_message.refresh_from_db()

    urls = chat_message.unique_citation_uris()

    assert urls[0][0] == "http://example.com"
    assert urls[0][1] == URL("http://example.com")
    assert urls[1][0] == "original_file.txt"
    assert urls[1][1].parts[-1] == "original_file.txt"


@pytest.mark.parametrize(("value", "expected"), [("invalid origin", None), ("Wikipedia", "Wikipedia")])
def test_try_parse_origin(value, expected):
    assert Citation.Origin.try_parse(value) == expected
