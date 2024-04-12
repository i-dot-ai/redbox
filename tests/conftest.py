import os

import boto3
import pytest
from botocore.exceptions import ClientError


@pytest.fixture
def file_pdf_path():
    path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "data",
        "pdf",
        "Cabinet Office - Wikipedia.pdf",
    )
    yield path


@pytest.fixture
def s3_client():
    client = boto3.client(
        "s3",
        aws_access_key_id="minioadmin",
        aws_secret_access_key="minioadmin",
        endpoint_url="http://localhost:9000",
    )

    try:
        client.create_bucket(
            Bucket="redbox-storage-dev",
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )
    except ClientError as e:
        if e.response["Error"]["Code"] != "BucketAlreadyOwnedByYou":
            raise e

    yield client


