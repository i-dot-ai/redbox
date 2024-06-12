import logging
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile, UploadedFile
from django.core.management import call_command
from redbox_app.redbox_core import client
from redbox_app.redbox_core.models import ChatHistory, ChatMessage, ChatRoleEnum, File, User, TextChunk



logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True, scope="session")
def _collect_static():
    call_command("collectstatic", "--no-input")


@pytest.fixture()
def create_user():
    def _create_user(email, date_joined_iso):
        date_joined = datetime.fromisoformat(date_joined_iso).astimezone(UTC)
        return User.objects.create_user(email=email, date_joined=date_joined)

    return _create_user


@pytest.fixture()
def alice(create_user):
    return create_user("alice@cabinetoffice.gov.uk", "2000-01-01")


@pytest.fixture()
def bob(create_user):
    return create_user("bob@example.com", "2000-01-01")


@pytest.fixture()
def chris(create_user):
    return create_user("chris@example.com", "2000-01-02")


@pytest.fixture()
def peter_rabbit():
    return User.objects.create_user(email="peter.rabbit@example.com", password="P455W0rd")


@pytest.fixture()
def jemima_puddleduck():
    return User.objects.create_user(email="jemima.puddleduck@example.com", password="P455W0rd")


@pytest.fixture()
def mrs_tiggywinkle():
    return User.objects.create_user(email="mrs.tiggywinkle@example.com")


@pytest.fixture()
def file_pdf_path() -> Path:
    return Path(__file__).parent / "data" / "pdf" / "Cabinet Office - Wikipedia.pdf"


@pytest.fixture()
def file_py_path() -> Path:
    return Path(__file__).parent / "data" / "py" / "test_data.py"


@pytest.fixture()
def s3_client():
    return client.s3_client()


@pytest.fixture()
def chat_history(alice: User) -> ChatHistory:
    session_id = uuid.uuid4()
    return ChatHistory.objects.create(id=session_id, users=alice)


@pytest.fixture()
def chat_message(chat_history: ChatHistory, uploaded_file: File) -> ChatMessage:
    chat_message = ChatMessage.objects.create(chat_history=chat_history, text="A question?", role=ChatRoleEnum.user)
    TextChunk(file=uploaded_file, chat_message=chat_message)
    return chat_message


@pytest.fixture()
def uploaded_file(alice: User, original_file: UploadedFile, s3_client) -> File:  # noqa: ARG001
    file = File.objects.create(
        user=alice, original_file=original_file, original_file_name=original_file.name, core_file_uuid=uuid.uuid4()
    )
    file.save()
    yield file
    file.delete()


@pytest.fixture()
def original_file() -> UploadedFile:
    return SimpleUploadedFile("original_file.txt", b"Lorem Ipsum.")


@pytest.fixture()
def chat_history_with_files(chat_history: ChatHistory, several_files: Sequence[File]) -> ChatHistory:
    ChatMessage.objects.create(chat_history=chat_history, text="A question?", role=ChatRoleEnum.user)
    chat_message = ChatMessage.objects.create(chat_history=chat_history, text="An answer.", role=ChatRoleEnum.ai)
    for file in several_files[0:2]:
        TextChunk(chat_message=chat_message, file=file)
    chat_message = ChatMessage.objects.create(
        chat_history=chat_history, text="Another question?", role=ChatRoleEnum.user
    )
    chat_message.selected_files.set(several_files[0:2])
    chat_message = ChatMessage.objects.create(chat_history=chat_history, text="Another answer.", role=ChatRoleEnum.ai)
    TextChunk(chat_message=chat_message, file=several_files[2])
    return chat_history


@pytest.fixture()
def several_files(alice: User, number_to_create: int = 4) -> Sequence[File]:
    files = []
    for i in range(number_to_create):
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
