from typing import Optional, Union
from uuid import uuid4

from langchain.chains.base import Chain
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from pydantic import Field, field_serializer

from redbox.models.base import PersistableModel


class ChatMessage(PersistableModel):
    uuid: str = Field(default_factory=lambda: str(uuid4()))
    # langchain.chains.base.Chain needs pydantic v1, breaks
    # https://python.langchain.com/docs/guides/pydantic_compatibility
    chain: Optional[object] = None
    message: object

    @field_serializer("chain")
    def serialise_chain(self, chain: Chain, _info):
        if isinstance(chain, Chain):
            return chain.dict()
        else:
            return chain

    @field_serializer("message")
    def serialise_message(
        self, message: Union[AIMessage, HumanMessage, SystemMessage], _info
    ):
        if isinstance(message, (AIMessage, HumanMessage, SystemMessage)):
            return message.dict()
        else:
            return message
