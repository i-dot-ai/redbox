from typing import Optional


from models.base import PersistableModel


class User(PersistableModel):
    email: Optional[str]
