import requests
from django.conf import settings

from redbox_app.redbox_core.models import User


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
