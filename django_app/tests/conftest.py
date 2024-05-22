import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile, UploadedFile
from django.core.management import call_command
from redbox_app.redbox_core import client
from redbox_app.redbox_core.models import ChatHistory, ChatMessage, ChatRoleEnum, File, User

logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True, scope="session")
def collect_static():
    call_command("collectstatic", "--no-input")


@pytest.fixture
def create_user():
    def _create_user(email, date_joined_iso):
        date_joined = datetime.fromisoformat(date_joined_iso).astimezone(UTC)
        user = User.objects.create_user(email=email, date_joined=date_joined)
        return user

    return _create_user


@pytest.fixture
def alice(create_user):
    return create_user("alice@cabinetoffice.gov.uk", "2000-01-01")


@pytest.fixture
def bob(create_user):
    return create_user("bob@example.com", "2000-01-01")


@pytest.fixture
def chris(create_user):
    return create_user("chris@example.com", "2000-01-02")


@pytest.fixture
def peter_rabbit():
    user = User.objects.create_user(email="peter.rabbit@example.com", password="P455W0rd")
    yield user


@pytest.fixture
def jemima_puddleduck():
    user = User.objects.create_user(email="jemima.puddleduck@example.com", password="P455W0rd")
    yield user


@pytest.fixture
def mrs_tiggywinkle():
    user = User.objects.create_user(email="mrs.tiggywinkle@example.com")
    yield user


@pytest.fixture
def file_pdf_path() -> Path:
    return Path(__file__).parent / "data" / "pdf" / "Cabinet Office - Wikipedia.pdf"


@pytest.fixture
def file_py_path() -> Path:
    return Path(__file__).parent / "data" / "py" / "test_data.py"


@pytest.fixture
def s3_client():
    yield client.s3_client()


@pytest.fixture
def chat_history(alice: User) -> ChatHistory:
    session_id = uuid.uuid4()
    chat_history = ChatHistory.objects.create(id=session_id, users=alice)
    yield chat_history
    chat_history.delete()


@pytest.fixture
def chat_message(chat_history: ChatHistory, uploaded_file: File) -> ChatMessage:
    chat_message = ChatMessage.objects.create(chat_history=chat_history, text="A question?", role=ChatRoleEnum.user)
    chat_message.source_files.set([uploaded_file])
    return chat_message


@pytest.fixture
def uploaded_file(alice: User, original_file: UploadedFile) -> File:
    file = File.objects.create(
        user=alice, original_file=original_file, original_file_name=original_file.name, core_file_uuid=uuid.uuid4()
    )
    return file


@pytest.fixture
def original_file() -> UploadedFile:
    return SimpleUploadedFile("original_file.txt", b"Lorem Ipsum.")
