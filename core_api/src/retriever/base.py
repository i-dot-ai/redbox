
from typing import TypedDict

from redbox.models.file import UUID

class ESQuery(TypedDict):
    question: str
    file_uuids: list[UUID]
    user_uuid: UUID