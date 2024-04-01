import uuid

from django.db import models
from django_use_email_as_username.models import BaseUser, BaseUserManager


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


# TO DO: Based on /redbox/models/file.py, but not complete
class File(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    path = models.TextField(help_text="location of file")
    name = models.TextField()
    processing_status = models.CharField(
        choices=ProcessingStatusEnum.choices, default=ProcessingStatusEnum.uploaded
    )

    def get_processing_text(self) -> str:
        processing_status_list = list(ProcessingStatusEnum)
        stage = processing_status_list.index(self.processing_status)
        if stage == len(processing_status_list) - 1:
            return self.processing_status
        return f"{stage + 1}/{len(processing_status_list) - 1} {self.processing_status}"
