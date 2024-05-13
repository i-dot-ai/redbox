import boto3
import requests
from botocore.exceptions import ClientError
from django.conf import settings
from redbox_app.redbox_core.models import User


def s3_client():
    if settings.OBJECT_STORE == "minio":
        client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_S3_SECRET_ACCESS_KEY,
            endpoint_url=f"http://{settings.MINIO_HOST}:{settings.MINIO_PORT}",
        )
    elif settings.OBJECT_STORE == "s3":
        client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_S3_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME,
        )
    elif settings.OBJECT_STORE == "moto":
        from moto import mock_aws

        mock = mock_aws()
        mock.start()

        client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_S3_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME,
        )
    else:
        raise NotImplementedError

    try:
        client.create_bucket(
            Bucket=settings.BUCKET_NAME,
            CreateBucketConfiguration={"LocationConstraint": settings.AWS_S3_REGION_NAME},
        )
    except ClientError as e:
        if e.response["Error"]["Code"] != "BucketAlreadyOwnedByYou":
            raise e
    return client


class CoreApiClient:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port

    @property
    def url(self) -> str:
        return f"{self.host}:{self.port}"

    def upload_file(self, bucket_name: str, name: str, user: User):
        if self.host == "testserver":
            file = {
                "key": name,
                "bucket": bucket_name,
            }
            return file

        response = requests.post(
            f"{self.url}/file", json={"key": name}, headers={"Authorization": user.get_bearer_token()}, timeout=30
        )
        if response.status_code != 201:
            raise ValueError(response.text)
        return response.json()

    def rag_chat(self, message_history: list[dict[str, str]], token: str) -> str:
        url = f"{self.url}/chat/rag"
        response = requests.post(
            url, json={"message_history": message_history}, headers={"Authorization": token}, timeout=60
        )
        return response.json()["output_text"]
