import json

import boto3
from botocore.exceptions import ClientError


def get_secrets(secret_name, region_name):
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager", region_name=region_name)

    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            print(f"The requested secret {secret_name} was not found.")
        elif e.response["Error"]["Code"] == "InvalidRequestException":
            print(f"The requested was invalid due to: {str(e)}.")
        elif e.response["Error"]["Code"] == "InvalidParameterException":
            print(f"The requested was invalid params: {str(e)}.")
        return None
    else:
        if "SecretString" in get_secret_value_response:
            return json.loads(get_secret_value_response)["SecretString"]
        else:
            print("Unsupported response")
            return None
