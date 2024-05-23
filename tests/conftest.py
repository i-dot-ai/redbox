from pathlib import Path

import boto3
import pytest
from botocore.exceptions import ClientError


@pytest.fixture()
def file_path() -> Path:
    return Path(__file__).parent / "data" / "html" / "example.html"


@pytest.fixture()
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

    return client


# store history of failures per test class name and per index in parametrize (if parametrize used)
_test_failed_incremental: dict[str, dict[tuple[int, ...], str]] = {}


def pytest_runtest_makereport(item, call):
    if "incremental" in item.keywords and call.excinfo is not None:
        # the test has failed
        # retrieve the class name of the test
        cls_name = str(item.cls)
        # retrieve the index of the test (if parametrize is used in combination with incremental)
        parametrize_index = tuple(item.callspec.indices.values()) if hasattr(item, "callspec") else ()
        # retrieve the name of the test function
        test_name = item.originalname or item.name
        # store in _test_failed_incremental the original name of the failed test
        _test_failed_incremental.setdefault(cls_name, {}).setdefault(parametrize_index, test_name)


def pytest_runtest_setup(item):
    if "incremental" in item.keywords:
        # retrieve the class name of the test
        cls_name = str(item.cls)
        # check if a previous test has failed for this class
        if cls_name in _test_failed_incremental:
            # retrieve the index of the test (if parametrize is used in combination with incremental)
            parametrize_index = tuple(item.callspec.indices.values()) if hasattr(item, "callspec") else ()
            # retrieve the name of the first test function to fail for this class name and index
            test_name = _test_failed_incremental[cls_name].get(parametrize_index, None)
            # if name found, test has failed for the combination of class name & test name
            if test_name is not None:
                pytest.xfail("previous test failed ({})".format(test_name))
