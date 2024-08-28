import logging
from uuid import UUID

import boto3
import requests
from botocore.exceptions import ClientError
from django.conf import settings
from yarl import URL

from redbox.models.file import File as CoreFile
from redbox_app.redbox_core.models import User

logger = logging.getLogger(__name__)


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


class CoreApiClient:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port

    @property
    def url(self) -> URL:
        return URL(f"http://{self.host}:{self.port}")

    def upload_file(self, name: str, user: User) -> CoreFile:
        response = requests.post(
            self.url / "file", json={"key": name}, headers={"Authorization": user.get_bearer_token()}, timeout=30
        )
        response.raise_for_status()
        core_file = response.json()
        core_file["creator_user_uuid"] = user.id
        return CoreFile(**core_file)

    def delete_file(self, file_id: UUID, user: User) -> CoreFile:
        url = self.url / "file" / str(file_id)
        response = requests.delete(url, headers={"Authorization": user.get_bearer_token()}, timeout=60)
        response.raise_for_status()
        core_file = response.json()
        core_file["creator_user_uuid"] = user.id
        return CoreFile(**core_file)
