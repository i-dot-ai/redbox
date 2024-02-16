from pydantic import Field, computed_field
from datetime import datetime
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel


class PersistableModel(BaseModel):
    uuid: str = Field(default_factory=lambda: str(uuid4()))
    created_datetime: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    creator_user_uuid: Optional[str] = None

    @computed_field
    def model_type(self) -> str:
        raise NotImplementedError
