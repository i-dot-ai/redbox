import boto3
import requests
from botocore.exceptions import ClientError
from django.conf import settings
from redbox_app.redbox_core.models import User


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
            raise e
    return client


class CoreApiClient:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def embed_file(self, name: str, user: User):
        response = requests.post(
            f"{self.url}/file", json={"key": name}, headers={"Authorization": user.get_bearer_token()}, timeout=30
        )
        if response.status_code != 201:
            raise ValueError(response.text)
        return response.json()

    def rag_chat(self, message_history: list[dict[str, str]], user: User) -> str:
        response = requests.post(
            f"{self.url}/chat/rag",
            json={"message_history": message_history},
            headers={"Authorization": user.get_bearer_token()},
            timeout=60,
        )
        if response.status_code != 200:
            raise ValueError(response.text)
        return response.json()["output_text"]
