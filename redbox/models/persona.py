from typing import Optional


from redbox.models.base import PersistableModel


class ChatPersona(PersistableModel):
    name: Optional[str]
    description: Optional[str]
    prompt: Optional[str]
