import os

import boto3
import pytest


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
    yield boto3.client(
        "s3",
        aws_access_key_id="minioadmin",
        aws_secret_access_key="minioadmin",
        endpoint_url=f"http://localhost:9000",
    )
