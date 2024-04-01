from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, computed_field


class PersistableModel(BaseModel):
    uuid: UUID = Field(default_factory=uuid4)
    created_datetime: datetime = Field(default_factory=datetime.utcnow)
    creator_user_uuid: Optional[UUID] = None

    @computed_field
    def model_type(self) -> str:
        return self.__class__.__name__
