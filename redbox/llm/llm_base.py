import json
import os
from datetime import date
from typing import List, Optional

import dotenv
from langchain.cache import SQLiteCache
from langchain.chains import MapReduceDocumentsChain, ReduceDocumentsChain
from langchain.chains.combine_documents.stuff import StuffDocumentsChain
from langchain.chains.llm import LLMChain
from langchain.chains.qa_with_sources import load_qa_with_sources_chain
from langchain.globals import set_llm_cache
from langchain.memory import ConversationBufferMemory
from langchain_community.embeddings import (
    HuggingFaceEmbeddings,
    SentenceTransformerEmbeddings,
)
from langchain_community.vectorstores import Chroma
from pyprojroot import here

from redbox.llm.prompts.chat import (
    CONDENSE_QUESTION_PROMPT,
    STUFF_DOCUMENT_PROMPT,
    WITH_SOURCES_PROMPT,
)
from redbox.llm.prompts.spotlight import SPOTLIGHT_COMBINATION_TASK_PROMPT
from redbox.llm.spotlight.spotlight import (
    key_actions_task,
    key_dates_task,
    key_discussion_task,
    key_people_task,
    summary_task,
)
from redbox.models.file import Chunk, File
from redbox.models.spotlight import Spotlight, SpotlightTask

dotenv.load_dotenv(os.path.join(here(), ".env"))


class LLMHandler(object):
    """A class to handle RedBox data suffused interactions with a given LLM"""

    def __init__(
        self,
        llm,
        user_uuid: Optional[str] = None,
        vector_store: Optional[Chroma] = None,
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
        self.cache = None
        if os.environ["CACHE_LLM_RESPONSES"] == "true":
            self.cache = SQLiteCache(database_path=os.environ["CACHE_LLM_DB"])
            set_llm_cache(self.cache)

        self.llm = llm
        self.user_uuid = user_uuid
        self.vector_store = vector_store

        if embedding_function is None:
            self.embedding_function = self._create_embedding_function()
        else:
            self.embedding_function = embedding_function

        if vector_store is None:  # if no vectorstore provided, make a new one
            self.vector_store = self._create_vector_store()
        else:
            self.vector_store = vector_store

        self.memory = ConversationBufferMemory(
            memory_key="chat_history", return_messages=True
        )

    def _create_vector_store(self) -> Chroma:
        """Initialises Chrome VectorDB on known DB dir in data

        Returns:
            Chroma: the langchain vectorstore object for Chroma
        """
        embedder = self.embedding_function
        persist_directory = os.path.join("data", self.user_uuid, "db")
        return Chroma(embedding_function=embedder, persist_directory=persist_directory)

    def _create_embedding_function(self) -> SentenceTransformerEmbeddings:
        """Initialises our vectorisation method.

        Returns:
            SentenceTransformerEmbeddings: object to run text embedding
        """
        return SentenceTransformerEmbeddings()

    def clear_cache(self) -> None:
        if self.cache is not None:
            self.cache.clear()

    def add_chunks_to_vector_store(self, chunks: List[Chunk]) -> None:
        """Takes a list of Chunks and embedds them into the vector store

        Args:
            chunks (List[Chunk]): The chunks to be added to the vector store
        """

        metadatas = [dict(chunk.metadata) for chunk in chunks]

        for i, chunk in enumerate(chunks):
            # add other chunk fields to metadata
            metadatas[i]["uuid"] = chunk.uuid
            metadatas[i]["parent_file_uuid"] = chunk.parent_file_uuid
            metadatas[i]["index"] = chunk.index
            metadatas[i]["created_datetime"] = chunk.created_datetime
            metadatas[i]["token_count"] = chunk.token_count
            metadatas[i]["text_hash"] = chunk.text_hash

        sanitised_metadatas = []

        for metadata in metadatas:
            for k, v in metadata.items():
                if isinstance(v, list) or isinstance(v, dict):
                    # Converting {k} metadata into JSON string to make vectorstore safe
                    metadata[k] = json.dumps(metadata[k], ensure_ascii=False)

            sanitised_metadatas.append(metadata)

        # it requires tha batch size to be smaller than 166 but some documents have >300 chunks
        batch_size = 160
        for i in range(0, len(chunks), batch_size):
            self.vector_store.add_texts(
                texts=[chunk.text for chunk in chunks[i : i + batch_size]],
                metadatas=[meta for meta in sanitised_metadatas[i : i + batch_size]],
                ids=[chunk.uuid for chunk in chunks[i : i + batch_size]],
            )

    def chat_with_rag(
        self,
        user_question: str,
        user_info: dict,
        chat_history: Optional[List] = [],
        callbacks: Optional[List] = [],
    ) -> dict:
        """Answers user question by retrieving context from content stored in
        Vector DB

        Args:
            user_question (str): The message or query being posed by user
            chat_history (list, optional): The message history of the chat to
            add context. Defaults to [].

        Returns:
            dict: A dictionary with the new chat_history:list and the answer
        """
        if os.environ["CACHE_LLM_RESPONSES"] == "true":
            set_llm_cache(SQLiteCache(database_path=os.environ["CACHE_LLM_DB"]))

        self.docs_with_sources_chain = load_qa_with_sources_chain(
            self.llm,
            chain_type="stuff",
            prompt=WITH_SOURCES_PROMPT,
            document_prompt=STUFF_DOCUMENT_PROMPT,
            verbose=True,
        )

        self.condense_question_chain = LLMChain(
            llm=self.llm, prompt=CONDENSE_QUESTION_PROMPT
        )

        # split chain manualy, so that the standalone question doesn't leak into chat
        # should we display some waiting message instead?
        standalone_question = self.condense_question_chain(
            {
                "question": user_question,
                "chat_history": chat_history,
                # "user_info": user_info,
                # "current_date": date.today().isoformat()
            }
        )["text"]

        docs = self.vector_store.as_retriever().get_relevant_documents(
            standalone_question,
        )

        result = self.docs_with_sources_chain(
            {
                "question": standalone_question,
                "input_documents": docs,
                "user_info": user_info,
                "current_date": date.today().isoformat(),
            },
            callbacks=callbacks,
        )
        return (result, self.docs_with_sources_chain)

    def get_spotlight_tasks(self, files: List[File], file_hash: str) -> Spotlight:
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
        callbacks: Optional[List] = [],
        map_reduce: bool = False,
        token_max: int = 100_000,
    ) -> dict:
        map_chain = LLMChain(llm=self.llm, prompt=task.prompt_template)
        regular_chain = StuffDocumentsChain(
            llm_chain=map_chain, document_variable_name="text"
        )

        reduce_chain = LLMChain(llm=self.llm, prompt=SPOTLIGHT_COMBINATION_TASK_PROMPT)
        combine_documents_chain = StuffDocumentsChain(
            llm_chain=reduce_chain, document_variable_name="text"
        )
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
            chain = map_reduce_chain
            result = map_reduce_chain.run(
                user_info=user_info,
                current_date=date.today().isoformat(),
                input_documents=spotlight.to_documents(),
                callbacks=callbacks,
            )
        else:
            chain = regular_chain
            result = regular_chain.run(
                user_info=user_info,
                current_date=date.today().isoformat(),
                input_documents=spotlight.to_documents(),
                callbacks=callbacks,
            )

        return (result, chain)
