from datetime import UTC, datetime
from typing import Any, Optional

from langchain.chains import MapReduceDocumentsChain, ReduceDocumentsChain
from langchain.chains.combine_documents.base import BaseCombineDocumentsChain
from langchain.chains.combine_documents.stuff import StuffDocumentsChain
from langchain.chains.llm import LLMChain
from langchain.chains.qa_with_sources import load_qa_with_sources_chain
from langchain.memory import ConversationBufferMemory
from langchain_community.embeddings import (
    HuggingFaceEmbeddings,
    SentenceTransformerEmbeddings,
)

from redbox.llm.prompts.chat import (
    CONDENSE_QUESTION_PROMPT,
    STUFF_DOCUMENT_PROMPT,
    WITH_SOURCES_PROMPT,
)
from redbox.llm.prompts.spotlight import SPOTLIGHT_COMBINATION_TASK_PROMPT
from redbox.llm.spotlight.spotlight import (
    key_actions_task,
    key_discussion_task,
    key_people_task,
    summary_task,
)
from redbox.models.file import File
from redbox.models.spotlight import Spotlight, SpotlightTask


class LLMHandler(object):
    """A class to handle RedBox data suffused interactions with a given LLM"""

    def __init__(
        self,
        llm,
        user_uuid: str,
        vector_store=None,
        embedding_function: Optional[HuggingFaceEmbeddings] = None,
    ):
        """Initialise LLMHandler

        Args:
            llm (_type_): _description_
            user_uuid: Session to load data from and save data to.
            vector_store (Optional[Chroma], optional): _description_.
            Defaults to None.
            embedding_function (Optional[HuggingFaceEmbeddings], optional):
            _description_. Defaults to None.
        """

        self.llm = llm
        self.user_uuid = user_uuid

        self.embedding_function = embedding_function or self._create_embedding_function()

        self.vector_store = vector_store

        self.memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

    def _create_embedding_function(self) -> SentenceTransformerEmbeddings:
        """Initialises our vectorisation method.

        Returns:
            SentenceTransformerEmbeddings: object to run text embedding
        """
        return SentenceTransformerEmbeddings()

    def chat_with_rag(
        self,
        user_question: str,
        user_info: dict,
        chat_history: Optional[list] = None,
        callbacks: Optional[list] = None,
    ) -> tuple[dict, BaseCombineDocumentsChain]:
        """Answers user question by retrieving context from content stored in
        Vector DB

        Args:
            user_question (str): The message or query being posed by user
            chat_history (list, optional): The message history of the chat to
            add context. Defaults to [].

        Returns:
            dict: A dictionary with the new chat_history:list and the answer
            BaseCombineDocumentsChain: docs-with-sources-chain
        """

        docs_with_sources_chain = load_qa_with_sources_chain(
            self.llm,
            chain_type="stuff",
            prompt=WITH_SOURCES_PROMPT,
            document_prompt=STUFF_DOCUMENT_PROMPT,
            verbose=True,
        )

        condense_question_chain = LLMChain(llm=self.llm, prompt=CONDENSE_QUESTION_PROMPT)

        # split chain manually, so that the standalone question doesn't leak into chat
        # should we display some waiting message instead?
        standalone_question = condense_question_chain(
            {
                "question": user_question,
                "chat_history": chat_history or [],
                # "user_info": user_info,
                # "current_date": date.today().isoformat()
            }
        )["text"]

        docs = self.vector_store.as_retriever().get_relevant_documents(
            standalone_question,
        )

        result = docs_with_sources_chain(
            {
                "question": standalone_question,
                "input_documents": docs,
                "user_info": user_info,
                "current_date": datetime.now(tz=UTC).date().isoformat(),
            },
            callbacks=callbacks or [],
        )
        return result, docs_with_sources_chain

    def get_spotlight_tasks(self, files: list[File], file_hash: str) -> Spotlight:
        spotlight = Spotlight(
            files=files,
            file_hash=file_hash,
            tasks=[
                summary_task,
                key_discussion_task,
                key_actions_task,
                key_people_task,
            ],
        )
        return spotlight

    def run_spotlight_task(
        self,
        spotlight: Spotlight,
        task: SpotlightTask,
        user_info: dict,
        callbacks: Optional[list] = None,
        map_reduce: bool = False,
        token_max: int = 100_000,
    ) -> tuple[Any, StuffDocumentsChain | MapReduceDocumentsChain]:
        map_chain = LLMChain(llm=self.llm, prompt=task.prompt_template)  # type: ignore
        regular_chain = StuffDocumentsChain(llm_chain=map_chain, document_variable_name="text")

        reduce_chain = LLMChain(llm=self.llm, prompt=SPOTLIGHT_COMBINATION_TASK_PROMPT)
        combine_documents_chain = StuffDocumentsChain(llm_chain=reduce_chain, document_variable_name="text")
        reduce_documents_chain = ReduceDocumentsChain(
            combine_documents_chain=combine_documents_chain,
            collapse_documents_chain=combine_documents_chain,
            token_max=token_max,
        )
        map_reduce_chain = MapReduceDocumentsChain(
            llm_chain=map_chain,
            reduce_documents_chain=reduce_documents_chain,
            document_variable_name="text",
            return_intermediate_steps=False,
        )

        if map_reduce:
            result = map_reduce_chain.run(
                user_info=user_info,
                current_date=datetime.now(tz=UTC).date().isoformat(),
                input_documents=spotlight.to_documents(),
                callbacks=callbacks or [],
            )
            return result, map_reduce_chain
        else:
            result = regular_chain.run(
                user_info=user_info,
                current_date=datetime.now(tz=UTC).date().isoformat(),
                input_documents=spotlight.to_documents(),
                callbacks=callbacks or [],
            )

            return result, regular_chain
