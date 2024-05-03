from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, computed_field


class PersistableModel(BaseModel):
    """Base class for all models that can be persisted to the database."""

    uuid: UUID = Field(default_factory=uuid4)
    created_datetime: datetime = Field(default_factory=datetime.utcnow)
    creator_user_uuid: UUID = Field(default_factory=uuid4)

    @computed_field
    def model_type(self) -> str:
        """Return the name of the model class.

        Returns:
            str: The name of the model class.
        """
        return self.__class__.__name__
