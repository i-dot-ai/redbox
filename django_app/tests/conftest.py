import logging
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path

import boto3
import pytest
from botocore.exceptions import ClientError
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile, UploadedFile
from django.core.management import call_command
from django.utils import timezone
from freezegun import freeze_time

from redbox_app.redbox_core.models import (
    AISettings,
    Chat,
    ChatLLMBackend,
    ChatMessage,
    ChatMessageTokenUse,
    Citation,
    File,
)

User = get_user_model()

logger = logging.getLogger(__name__)


@pytest.fixture()
def s3_client():
    if settings.OBJECT_STORE == "s3":
        client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_S3_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME,
        )
    else:
        client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_S3_SECRET_ACCESS_KEY,
            endpoint_url=f"http://{settings.MINIO_HOST}:{settings.MINIO_PORT}",
        )

    try:
        client.create_bucket(
            Bucket=settings.BUCKET_NAME,
            CreateBucketConfiguration={"LocationConstraint": settings.AWS_S3_REGION_NAME},
        )
    except ClientError as e:
        if e.response["Error"]["Code"] != "BucketAlreadyOwnedByYou":
            raise
    return client


@pytest.fixture(autouse=True, scope="session")
def _collect_static():
    call_command("collectstatic", "--no-input")


@pytest.fixture(autouse=True)
def default_ai_settings(db):  # noqa: ARG001
    gpt_4o, _ = ChatLLMBackend.objects.get_or_create(name="gpt-4o", provider="azure_openai", is_default=True)
    ai_settings, _ = AISettings.objects.get_or_create(label="default", chat_backend=gpt_4o)
    return ai_settings


@pytest.fixture()
def create_user():
    def _create_user(
        email,
        date_joined_iso,
        is_staff=False,
        grade=User.UserGrade.DIRECTOR,
        business_unit=User.BusinessUnit.GOVERNMENT_BUSINESS_SERVICES,
        profession=User.Profession.IA,
        ai_experience=User.AIExperienceLevel.EXPERIENCED_NAVIGATOR,
    ):
        date_joined = datetime.fromisoformat(date_joined_iso).astimezone(UTC)
        return User.objects.create_user(
            email=email,
            date_joined=date_joined,
            is_staff=is_staff,
            grade=grade,
            business_unit=business_unit,
            profession=profession,
            ai_experience=ai_experience,
        )

    return _create_user


@pytest.fixture()
def alice(create_user):
    return create_user(
        "alice@cabinetoffice.gov.uk",
        "2000-01-01",
    )


@pytest.fixture()
def chat_with_alice(alice):
    return Chat.objects.create(name="a chat", user=alice)


@pytest.fixture()
def bob(create_user):
    return create_user("bob@example.com", "2000-01-01")


@pytest.fixture()
def peter_rabbit():
    return User.objects.create_user(email="peter.rabbit@example.com", password="P455W0rd")


@pytest.fixture()
def user_with_demographic_data() -> User:
    return User.objects.create_user(
        name="Sir Gregory Pitkin",
        ai_experience=User.AIExperienceLevel.EXPERIENCED_NAVIGATOR,
        email="mrs.tiggywinkle@example.com",
        grade="DG",
        business_unit="Prime Minister's Office",
        profession="AN",
    )


@pytest.fixture()
def staff_user(create_user):
    return create_user("staff@example.com", "2000-01-01", True)


@pytest.fixture()
def superuser() -> User:
    return User.objects.create_superuser("super@example.com", "2000-01-01")


@pytest.fixture()
def file_pdf_path() -> Path:
    return Path(__file__).parent / "data" / "pdf" / "Cabinet Office - Wikipedia.pdf"


@pytest.fixture()
def file_py_path() -> Path:
    return Path(__file__).parent / "data" / "py" / "test_data.py"


@pytest.fixture()
def chat(alice: User) -> Chat:
    session_id = uuid.uuid4()
    return Chat.objects.create(id=session_id, user=alice, name="A chat")


@pytest.fixture()
def chat_with_message(chat: Chat) -> Chat:
    ChatMessage.objects.create(chat=chat, text="today", role=ChatMessage.Role.user)
    return chat


@pytest.fixture()
def chat_message(chat: Chat, uploaded_file: File) -> ChatMessage:
    chat_message = ChatMessage.objects.create(
        chat=chat, text="A question?", role=ChatMessage.Role.user, route="A route"
    )
    chat_message.source_files.set([uploaded_file])
    return chat_message


@pytest.fixture()
def chat_message_with_citation(chat: Chat, uploaded_file: File) -> ChatMessage:
    chat_message = ChatMessage.objects.create(
        chat=chat,
        text="An answer.",
        role=ChatMessage.Role.ai,
        rating=3,
        rating_chips=["apple", "pear"],
        rating_text="not bad",
        route="chat",
    )
    Citation.objects.create(file=uploaded_file, chat_message=chat_message, text="Lorem ipsum.")
    return chat_message


@pytest.fixture()
def chat_message_with_citation_and_tokens(chat_message_with_citation: ChatMessage) -> ChatMessage:
    chat_message = chat_message_with_citation
    ChatMessageTokenUse.objects.create(
        chat_message=chat_message, use_type=ChatMessageTokenUse.UseType.INPUT, model_name="gpt-4o", token_count=20
    )
    ChatMessageTokenUse.objects.create(
        chat_message=chat_message, use_type=ChatMessageTokenUse.UseType.OUTPUT, model_name="gpt-4o", token_count=200
    )
    return chat_message


@pytest.fixture()
def uploaded_file(alice: User, original_file: UploadedFile, s3_client) -> File:  # noqa: ARG001
    file = File.objects.create(
        user=alice,
        original_file=original_file,
        last_referenced=datetime.now(tz=UTC) - timedelta(days=14),
        status=File.Status.processing,
    )
    file.save()
    yield file
    file.citation_set.all().delete()
    file.delete()


@pytest.fixture()
def original_file() -> UploadedFile:
    return SimpleUploadedFile("original_file.txt", b"Lorem Ipsum.")


@pytest.fixture()
def chat_with_files(chat: Chat, several_files: Sequence[File]) -> Chat:
    ChatMessage.objects.create(
        chat=chat,
        text="A question?",
        role=ChatMessage.Role.user,
    )
    chat_message = ChatMessage.objects.create(
        chat=chat,
        text="An answer.",
        role=ChatMessage.Role.ai,
        route="search",
    )
    chat_message.source_files.set(several_files[0::2])
    chat_message = ChatMessage.objects.create(
        chat=chat,
        text="A second question?",
        role=ChatMessage.Role.user,
    )
    chat_message.selected_files.set(several_files[0:2])
    chat_message = ChatMessage.objects.create(
        chat=chat,
        text="A second answer.",
        role=ChatMessage.Role.ai,
        route="search",
    )
    chat_message.source_files.set([several_files[2]])
    return chat


@pytest.fixture()
def user_with_chats_with_messages_over_time(alice: User) -> User:
    now = timezone.now()
    with freeze_time(now - timedelta(days=40)):
        chats = [
            Chat.objects.create(id=uuid.uuid4(), user=alice, name="40 days old"),
            Chat.objects.create(id=uuid.uuid4(), user=alice, name="20 days old"),
            Chat.objects.create(id=uuid.uuid4(), user=alice, name="5 days old"),
            Chat.objects.create(id=uuid.uuid4(), user=alice, name="yesterday"),
            Chat.objects.create(id=uuid.uuid4(), user=alice, name="today"),
        ]
        ChatMessage.objects.create(
            chat=chats[0],
            text="40 days old",
            role=ChatMessage.Role.user,
        )
    with freeze_time(now - timedelta(days=20)):
        ChatMessage.objects.create(
            chat=chats[1],
            text="20 days old",
            role=ChatMessage.Role.user,
        )
    with freeze_time(now - timedelta(days=5)):
        ChatMessage.objects.create(
            chat=chats[2],
            text="5 days old",
            role=ChatMessage.Role.user,
        )
    with freeze_time(now - timedelta(days=1)):
        ChatMessage.objects.create(
            chat=chats[3],
            text="yesterday",
            role=ChatMessage.Role.user,
        )
    ChatMessage.objects.create(chat=chats[4], text="today", role=ChatMessage.Role.user)

    return alice


@pytest.fixture()
def several_files(alice: User, number_to_create: int = 4) -> Sequence[File]:
    files = []
    for i in range(number_to_create):
        filename = f"original_file_{i}.txt"
        files.append(
            File.objects.create(
                user=alice,
                original_file=SimpleUploadedFile(filename, b"Lorem Ipsum."),
                status=File.Status.complete,
            )
        )
    return files


@pytest.fixture()
def chat_message_with_rating(chat_message: ChatMessage) -> ChatMessage:
    chat_message.rating = 3
    chat_message.rating_text = "Ipsum Lorem."
    chat_message.rating_chips = ["speed", "accuracy", "blasphemy"]
    chat_message.save()
    return chat_message
