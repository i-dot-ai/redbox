from typing import List, Optional

from langchain.chains.base import Chain
from langchain.prompts import PromptTemplate
from langchain_core.documents import Document
from pydantic import field_serializer

from redbox.models.base import PersistableModel
from redbox.models.file import File


class SpotlightTask(PersistableModel):
    id: str
    title: str
    # langchain.prompts.PromptTemplate needs pydantic v1, breaks
    # https://python.langchain.com/docs/guides/pydantic_compatibility
    prompt_template: object

    def __hash__(self):
        return hash((type(self),) + (self.id, self.title))

    @field_serializer("prompt_template")
    def serialise_prompt(self, prompt_template: PromptTemplate, _info):
        if isinstance(prompt_template, PromptTemplate):
            return prompt_template.dict()
        else:
            return prompt_template


class SpotlightTaskComplete(PersistableModel):
    id: str
    title: str
    # langchain.chains.base.Chain needs pydantic v1, breaks
    # https://python.langchain.com/docs/guides/pydantic_compatibility
    chain: object
    file_hash: str
    raw: str
    processed: Optional[str] = None

    @field_serializer("chain")
    def serialise_chain(self, chain: Chain, _info):
        if isinstance(chain, Chain):
            return chain.dict()
        else:
            return chain


class Spotlight(PersistableModel):
    files: List[File]
    file_hash: str
    tasks: List[SpotlightTask]

    def to_documents(self) -> List[Document]:
        return [file.to_document() for file in self.files]


class SpotlightComplete(PersistableModel):
    file_hash: str
    file_uuids: List[str]
    tasks: List[SpotlightTaskComplete]
