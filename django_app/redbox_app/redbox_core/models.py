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
    original_file = models.FileField(storage=settings.BUCKET_NAME)
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

    def get_processing_text(self) -> str:
        processing_status_list = list(ProcessingStatusEnum)
        stage = processing_status_list.index(self.processing_status)
        if stage == len(processing_status_list) - 1:
            return self.processing_status
        return f"{stage + 1}/{len(processing_status_list) - 1} {self.processing_status}"


class ChatHistory(UUIDPrimaryKeyBase, TimeStampedModel):
    name = models.TextField(max_length=1024, null=False, blank=False)
    users = models.ManyToManyField(User)
    files_received = models.ForeignKey(File, on_delete=models.CASCADE, related_name="files_received")
    files_retrieved = models.ForeignKey(File, on_delete=models.CASCADE, related_name="files_retrieved")


class ChatMessage(UUIDPrimaryKeyBase, TimeStampedModel):
    chat_history = models.ForeignKey(ChatHistory, on_delete=models.CASCADE)
    text = models.TextField(max_length=32768, null=False, blank=False)
    role = models.TextField(max_length=1024, null=False, blank=False)
