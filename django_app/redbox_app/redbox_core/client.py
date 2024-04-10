import boto3
from botocore.exceptions import ClientError
from django.conf import settings
import requests


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
                CreateBucketConfiguration={"LocationConstraint": settings.AWS_REGION},
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

    def upload_file(self, s3_url: str, name: str, extension: str):
        if self.host ==  "testserver":
            file = {
                "extension": ".pdf",
                "key": "my-test-file.pdf",
            }
            return file

        response = requests.post(
            f"{self.url}/file",
            json={"presigned_url": s3_url}
        )
        if response.status_code != 201:
            raise ValueError(response.text)
        return response.json()
