from typing import List, Optional, Union

from langchain.chains.base import Chain
from pydantic import field_serializer

from redbox.models.base import PersistableModel


class Feedback(PersistableModel):
    input: Union[str, List[str]]
    # langchain.chains.base.Chain needs pydantic v1, breaks
    # https://python.langchain.com/docs/guides/pydantic_compatibility
    chain: Optional[object] = None
    output: str
    feedback_type: str
    feedback_score: str
    feedback_text: Optional[str] = None

    @field_serializer("chain")
    def serialise_chain(self, chain: Chain, _info):
        if isinstance(chain, Chain):
            return chain.dict()
        else:
            return chain
