from enum import StrEnum

from pydantic import BaseModel


from redbox.models.chat import ChatRoute


class RedboxEventType(StrEnum):
    on_metadata_generation = "on_metadata_generation"
    response_tokens = "response_tokens"
    activity = "activity"


class RedboxActivityEvent(BaseModel):
    message: str


FINAL_RESPONSE_TAG = "response_flag"
SOURCE_DOCUMENTS_TAG = "source_documents_flag"
ROUTE_NAME_TAG = "route_flag"
ROUTABLE_KEYWORDS = {ChatRoute.search: "Search for an answer to the question in the document"}
