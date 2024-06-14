from operator import itemgetter
from typing import Any, TypedDict, List, Dict
from uuid import UUID

from elasticsearch import Elasticsearch
from langchain.schema import StrOutputParser
from langchain_community.chat_models import ChatLiteLLM
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableLambda, RunnablePassthrough, chain
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_elasticsearch import ElasticsearchRetriever

from core_api.src.format import format_chunks
from redbox.models import Chunk, ChatMessage, ChatResponse
from redbox.models.chat import SourceDocument
from redbox.llm.prompts.chat import CONDENSE_QUESTION_PROMPT


def make_chat_prompt_from_messages_runnable(
    system_prompt: str,
    question_prompt: str
):
    system_prompt_message = [("system", system_prompt)]
    @chain
    def chat_prompt_from_messages(input_dict: Dict):
        """
        Create a ChatPrompTemplate as part of a chain using 'chat_history'. 
        Returns the PromptValue using values in the input_dict
        """
        return ChatPromptTemplate.from_messages(
            system_prompt_message +
            [
            (msg.role, msg.text) 
            for msg in input_dict['chat_history']
            ] + 
            [("user", question_prompt)]
        ).invoke(input_dict)
    return chat_prompt_from_messages


def make_static_response_chain(prompt_template):
    return (
        RunnablePassthrough.assign(
            response=(
                ChatPromptTemplate.from_template(prompt_template) 
                | RunnableLambda(lambda p: p.messages[0].content)
            ),
            source_documents=RunnableLambda(lambda x: []),
        )
    )


@chain
def map_to_chat_response(input_dict: Dict):
    """
    Create a ChatResponse at the end of a chain from a dict containing
    'response' a string to use as output_text 
    'source_documents' a list of chunks to map to source_documents
    """
    return ChatResponse(
        output_text=input_dict['response'],
        source_documents=[
            SourceDocument(
                page_content=chunk.text,
                file_uuid=chunk.parent_file_uuid,
                page_numbers=[chunk.metadata.page_number]
            )
            for chunk in input_dict['source_documents']
        ]
    )


def make_chat_runnable(
    system_prompt: str,
    llm: ChatLiteLLM,
) -> Runnable:
    """Takes a system prompt and LLM returns a chat runnable.

    Runnable takes input of a dict keyed to question and messages.

    Runnable returns a string.
    """
    chat_history = [
        ("system", system_prompt),
        ("placeholder", "{messages}"),
        ("user", "{question}"),
    ]

    return (
        {
            "question": itemgetter("question"),
            "messages": itemgetter("messages"),
        }
        | ChatPromptTemplate.from_messages(chat_history)
        | llm
        | StrOutputParser()
    )
