import os

import requests


def main(event, context):
    print(os.environ.get("MESSAGE", "No message found in env vars!"))
    response = requests.get("https://catfact.ninja/fact")
    return response.json()
