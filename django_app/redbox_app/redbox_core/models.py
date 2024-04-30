import uuid

from django.db import models
from django_use_email_as_username.models import BaseUser, BaseUserManager
from django.conf import settings


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


class ProcessingStatusEnum(models.TextChoices):
    uploaded = "uploaded"
    parsing = "parsing"
    chunking = "chunking"
    embedding = "embedding"
    indexing = "indexing"
    complete = "complete"


class File(UUIDPrimaryKeyBase, TimeStampedModel):
    processing_status = models.CharField(choices=ProcessingStatusEnum.choices, null=False, blank=False)
    original_file = models.FileField(storage=settings.AWS_STORAGE_BUCKET_NAME)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    @property
    def file_type(self):
        name = self.original_file.name
        return name.split(".")[-1]

    @property
    def file_url(self):
        return self.original_file.url

    @property
    def name(self):
        return self.original_file.name


class ChatHistory(UUIDPrimaryKeyBase, TimeStampedModel):
    name = models.TextField(max_length=1024, null=False, blank=False)
    users = models.ForeignKey(User, on_delete=models.CASCADE)
    source_files = models.ManyToManyField(File)


class ChatRoleEnum(models.TextChoices):
    ai = "ai"
    user = "user"
    system = "system"


class ChatMessage(UUIDPrimaryKeyBase, TimeStampedModel):
    chat_history = models.ForeignKey(ChatHistory, on_delete=models.CASCADE)
    text = models.TextField(max_length=32768, null=False, blank=False)
    role = models.CharField(choices=ChatRoleEnum.choices, null=False, blank=False)
    source_files = models.ManyToManyField(File)
