import boto3
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
                "url": "s3 url",
                "content_type": "application/pdf",
                "name": "my-test-file.pdf",
                "text": "once upon a time....",
                "processing_status": "uploaded"
            }
            return file

        response = requests.post(
            f"{self.url}/file",
            params={
                "name": name,
                "type": extension,
                "location": s3_url,
            },
        )
        if response.status_code != 201:
            raise ValueError(response.text)
        return response.json()
