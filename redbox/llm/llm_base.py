from datetime import UTC, datetime

from langchain.chains.combine_documents.base import BaseCombineDocumentsChain
from langchain.chains.llm import LLMChain
from langchain.chains.qa_with_sources import load_qa_with_sources_chain
from langchain.memory import ConversationBufferMemory
from langchain_community.embeddings import (
    HuggingFaceEmbeddings,
    SentenceTransformerEmbeddings,
)
from langchain_core.prompts import PromptTemplate

from redbox.models import Settings

env = Settings()


class LLMHandler:
    """A class to handle RedBox data suffused interactions with a given LLM"""

    def __init__(
        self,
        llm,
        user_uuid: str,
        vector_store=None,
        embedding_function: HuggingFaceEmbeddings | None = None,
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
        chat_history: list | None = None,
        callbacks: list | None = None,
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
            prompt=PromptTemplate.from_template(env.ai.core_redbox_prompt + env.ai.with_sources_prompt),
            document_prompt=PromptTemplate.from_template(env.ai.stuff_document_prompt),
            verbose=True,
        )

        condense_question_chain = LLMChain(
            llm=self.llm, prompt=PromptTemplate.from_template(env.ai.condense_question_prompt)
        )

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
