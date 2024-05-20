import uuid

import boto3
from botocore.config import Config
from django.conf import settings
from django.db import models
from django_use_email_as_username.models import BaseUser, BaseUserManager
from jose import jwt
from yarl import URL


class UUIDPrimaryKeyBase(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(editable=False, auto_now_add=True)
    modified_at = models.DateTimeField(editable=False, auto_now=True)

    class Meta:
        abstract = True
        ordering = ["created_at"]


class User(BaseUser, UUIDPrimaryKeyBase):
    username = None
    verified = models.BooleanField(default=False, blank=True, null=True)
    invited_at = models.DateTimeField(default=None, blank=True, null=True)
    invite_accepted_at = models.DateTimeField(default=None, blank=True, null=True)
    last_token_sent_at = models.DateTimeField(editable=False, blank=True, null=True)
    password = models.CharField("password", max_length=128, blank=True, null=True)
    objects = BaseUserManager()

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.email}"

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
    unknown = "unknown"


class File(UUIDPrimaryKeyBase, TimeStampedModel):
    processing_status = models.CharField(choices=ProcessingStatusEnum.choices, null=False, blank=False)
    original_file = models.FileField(storage=settings.STORAGES["default"]["BACKEND"])
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    original_file_name = models.TextField(max_length=2048, blank=True, null=True)
    core_file_uuid = models.UUIDField(null=True)

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.original_file_name} {self.user}"

    def delete(self, using=None, keep_parents=False):
        #  Needed to make sure no orphaned files remain in the storage
        self.original_file.storage.delete(self.original_file.name)
        super().delete()

    @property
    def file_type(self) -> str:
        name = self.original_file.name
        return name.split(".")[-1]

    @property
    def url(self) -> URL:
        #  In dev environment, get pre-signed url from minio
        if settings.ENVIRONMENT == "LOCAL":
            s3 = boto3.client(
                "s3",
                endpoint_url="http://localhost:9000",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_S3_SECRET_ACCESS_KEY,
                config=Config(signature_version="s3v4"),
                region_name=settings.AWS_S3_REGION_NAME,
            )

            url = s3.generate_presigned_url(
                ClientMethod="get_object",
                Params={
                    "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
                    "Key": self.name,
                },
            )
            return URL(url)
        else:
            return URL(self.original_file.url)

    @property
    def name(self) -> str:
        # User-facing name
        return self.original_file_name if self.original_file_name else self.original_file.name

    @property
    def unique_name(self) -> str:
        # Name used by core-api
        return self.original_file.file.name

    def get_processing_status_text(self) -> str:
        return next(
            (status[1] for status in ProcessingStatusEnum.choices if self.processing_status == status[0]),
            "Unknown",
        )


class ChatHistory(UUIDPrimaryKeyBase, TimeStampedModel):
    name = models.TextField(max_length=1024, null=False, blank=False)
    users = models.ForeignKey(User, on_delete=models.CASCADE)
    selected_files = models.ManyToManyField(
        File,
        related_name="chat_histories",
        blank=True,
    )

    class Meta:
        verbose_name_plural = "Chat history"

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.name} - {self.users}"


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

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.chat_history} - {self.text} - {self.role}"
