import boto3
from django.conf import settings


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
