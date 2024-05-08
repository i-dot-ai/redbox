import boto3
import requests
from botocore.exceptions import ClientError
from django.conf import settings
from redbox_app.redbox_core.models import User


def s3_client():
    if settings.OBJECT_STORE == "minio":
        client = boto3.client(
            "s3",
            aws_access_key_id=settings.MINIO_ACCESS_KEY,
            aws_secret_access_key=settings.MINIO_SECRET_KEY,
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


# TODO: rewrite with env vars
# if settings.OBJECT_STORE == "s3":
#     client = boto3.client(
#         "s3",
#         aws_access_key_id=???,
#         aws_secret_access_key=???,
#         region_name=settings.AWS_S3_REGION_NAME,
#     )
#     return client


class CoreApiClient:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port

    @property
    def url(self) -> str:
        return f"{self.host}:{self.port}"

    def upload_file(self, name: str, user: User):
        if self.host == "testserver":
            file = {
                "key": name,
                "bucket": settings.BUCKET_NAME,
            }
            return file

        response = requests.post(
            f"{self.url}/file",
            json={"key": name},
            headers={"Authorization": user.get_bearer_token()},
        )
        if response.status_code != 201:
            raise ValueError(response.text)
        return response.json()
