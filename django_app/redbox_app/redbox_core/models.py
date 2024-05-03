import uuid

from django.conf import settings
from django.db import models
from django_use_email_as_username.models import BaseUser, BaseUserManager
from dotenv import load_dotenv
from jose import jwt

load_dotenv()


class UUIDPrimaryKeyBase(models.Model):
    class Meta:
        abstract = True

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(editable=False, auto_now_add=True)
    modified_at = models.DateTimeField(editable=False, auto_now=True)

    class Meta:
        abstract = True
        ordering = ["created_at"]


class User(BaseUser, UUIDPrimaryKeyBase):
    objects = BaseUserManager()
    username = None
    verified = models.BooleanField(default=False, blank=True, null=True)
    invited_at = models.DateTimeField(default=None, blank=True, null=True)
    invite_accepted_at = models.DateTimeField(default=None, blank=True, null=True)
    last_token_sent_at = models.DateTimeField(editable=False, blank=True, null=True)

    def save(self, *args, **kwargs):
        self.email = self.email.lower()
        super().save(*args, **kwargs)

    def get_bearer_token(self) -> str:
        """the bearer token expected by the core-api"""
        user_uuid = str(self.id)
        bearer_token = jwt.encode({"user_uuid": user_uuid}, key=settings.SECRET_KEY)
        return f"Bearer {bearer_token}"


class ProcessingStatusEnum(models.TextChoices):
    uploaded = "uploaded"
    parsing = "parsing"
    chunking = "chunking"
    embedding = "embedding"
    indexing = "indexing"
    complete = "complete"


class File(UUIDPrimaryKeyBase, TimeStampedModel):
    processing_status = models.CharField(
        choices=ProcessingStatusEnum.choices, null=False, blank=False
    )
    original_file = models.FileField(storage=settings.DEFAULT_FILE_STORAGE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    original_file_name = models.TextField(max_length=2048, blank=True, null=True)

    @property
    def file_type(self):
        name = self.original_file.name
        return name.split(".")[-1]

    @property
    def url(self):
        return self.original_file.url

    @property
    def name(self):
        return (
            self.original_file_name
            if self.original_file_name
            else self.original_file.name
        )

    def get_processing_status_text(self) -> str:
        status = [
            status
            for status in ProcessingStatusEnum.choices
            if self.processing_status == status[0]
        ][0][1]
        return status if status else "Unknown"


class ChatHistory(UUIDPrimaryKeyBase, TimeStampedModel):
    name = models.TextField(max_length=1024, null=False, blank=False)
    users = models.ForeignKey(User, on_delete=models.CASCADE)
    selected_files = models.ManyToManyField(
        File,
        related_name="chat_histories",
        blank=True,
    )


class ChatRoleEnum(models.TextChoices):
    ai = "ai"
    user = "user"
    system = "system"


class ChatMessage(UUIDPrimaryKeyBase, TimeStampedModel):
    chat_history = models.ForeignKey(ChatHistory, on_delete=models.CASCADE)
    text = models.TextField(max_length=32768, null=False, blank=False)
    role = models.CharField(choices=ChatRoleEnum.choices, null=False, blank=False)
    source_files = models.ManyToManyField(
        File,
        related_name="chat_messages",
        blank=True,
    )
