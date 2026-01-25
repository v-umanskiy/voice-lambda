import json
import os
from typing import TypedDict

import boto3


class ApiConfig(TypedDict):
    openai_api_key: str
    gemini_api_key: str


_secrets_client = boto3.client("secretsmanager")


def get_api_config() -> ApiConfig:
    secret_id = os.environ["SECRETS_ARN"]
    secret_value = _secrets_client.get_secret_value(SecretId=secret_id)
    secret_string = secret_value["SecretString"]

    payload = json.loads(secret_string)
    return {
        "openai_api_key": payload["OPENAI_API_KEY"],
        "gemini_api_key": payload["GEMINI_API_KEY"],
    }
