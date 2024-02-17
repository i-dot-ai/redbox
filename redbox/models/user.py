from typing import Optional


from redbox.models.base import PersistableModel


class User(PersistableModel):
    email: Optional[str]
