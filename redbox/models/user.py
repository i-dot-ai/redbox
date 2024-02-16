from typing import Optional

from pydantic import computed_field

from redbox.models.base import PersistableModel


class User(PersistableModel):
    email: Optional[str]

    @computed_field(return_type=str)
    def model_type(self) -> str:
        return self.__class__.__name__
