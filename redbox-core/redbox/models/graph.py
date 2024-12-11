from enum import StrEnum

from pydantic import BaseModel


class RedboxEventType(StrEnum):
    on_metadata_generation = "on_metadata_generation"
    response_tokens = "response_tokens"
    activity = "activity"
    on_source_report = "on_source_report"  # Previous 'documents used' sources
    on_citations_report = "on_citations_report"  # New footnote level citations


class RedboxActivityEvent(BaseModel):
    message: str


FINAL_RESPONSE_TAG = "response_flag"
SOURCE_DOCUMENTS_TAG = "source_documents_flag"
ROUTE_NAME_TAG = "route_flag"
