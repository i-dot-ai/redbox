from datetime import datetime
from typing import Annotated, Optional
from uuid import UUID, uuid4

from pydantic import AfterValidator, BaseModel, Field, computed_field


class PersistableModel(BaseModel):
    uuid: UUID | Annotated[str, AfterValidator(lambda x: UUID(x))] = Field(default_factory=uuid4)
    created_datetime: datetime = Field(default_factory=datetime.utcnow)
    creator_user_uuid: Optional[UUID | Annotated[str, AfterValidator(lambda x: UUID(x))]] = None

    @computed_field
    def model_type(self) -> str:
        return self.__class__.__name__
