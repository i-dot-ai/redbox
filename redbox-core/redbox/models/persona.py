from redbox.models.base import PersistableModel


class ChatPersona(PersistableModel):
    name: str | None
    description: str | None
    prompt: str | None
