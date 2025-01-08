from enum import StrEnum

from pydantic import BaseModel


class RedboxEventType(StrEnum):
    on_metadata_generation = "on_metadata_generation"
    response_tokens = "response_tokens"


class RedboxActivityEvent(BaseModel):
    message: str


FINAL_RESPONSE_TAG = "response_flag"
SOURCE_DOCUMENTS_TAG = "source_documents_flag"
ROUTE_NAME_TAG = "route_flag"
