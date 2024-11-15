from pydantic import BaseModel


class AITestCase(BaseModel):
    id: str  # Has to be file path valid
    prompts: list[str]
    documents: list[str]
