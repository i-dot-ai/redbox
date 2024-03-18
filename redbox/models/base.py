from datetime import datetime
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field, computed_field


class PersistableModel(BaseModel):
    uuid: str = Field(default_factory=lambda: str(uuid4()))
    created_datetime: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    creator_user_uuid: Optional[str] = None

    @computed_field
    def model_type(self) -> str:
        return self.__class__.__name__
