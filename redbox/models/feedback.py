from datetime import datetime
from typing import List, Optional, Union
from uuid import uuid4

from langchain.chains.base import Chain
from pydantic import BaseModel, Field, computed_field, field_serializer


class Feedback(BaseModel):
    uuid: str = Field(default_factory=lambda: str(uuid4()))
    input: Union[str, List[str]]
    # langchain.chains.base.Chain needs pydantic v1, breaks
    # https://python.langchain.com/docs/guides/pydantic_compatibility
    chain: Optional[object] = None
    output: str
    feedback_type: str
    feedback_score: str
    feedback_text: Optional[str] = None
    created_datetime: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    creator_user_uuid: Optional[str]

    @computed_field
    def model_type(self) -> str:
        return self.__class__.__name__

    @field_serializer("chain")
    def serialise_chain(self, chain: Chain, _info):
        if isinstance(chain, Chain):
            return chain.dict()
        else:
            return chain
