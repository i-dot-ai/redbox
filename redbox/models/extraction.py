from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, computed_field


class Action(BaseModel):
    uuid: str = Field(default_factory=lambda: str(uuid4()))
    date: str = Field(description="The deadline or completion date of the action")
    action: str = Field(description="The item to be actioned")

    created_datetime: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    @computed_field
    def model_type(self) -> str:
        return self.__class__.__name__


class SpotlightSummaryExtraction(BaseModel):
    uuid: str = Field(default_factory=lambda: str(uuid4()))
    people_names: List[str] = Field(
        description=(
            "A complete list of all people: the first name, last name and "
            "titles of important people. No job titles."
        )
    )
    organisation_names: List[str] = Field(
        description=(
            "A complete list of all important organisations, institutions, "
            "and government departments"
        )
    )
    actions: List[Action] = Field(
        description=(
            "A complete list of all important actions with deadlines, in the "
            "format <date>, <action>"
        )
    )

    created_datetime: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    creator_user_uuid: Optional[str]

    @computed_field
    def model_type(self) -> str:
        return self.__class__.__name__
