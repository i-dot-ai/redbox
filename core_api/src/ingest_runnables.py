
from uuid import uuid4
from typing import List, TYPE_CHECKING
from functools import reduce, wraps
from operator import itemgetter
from pathlib import Path
from dataclasses import dataclass

from pydantic import Field
from elasticsearch import Elasticsearch

from langchain_text_splitters.character import RecursiveCharacterTextSplitter
from langchain_community.chat_models import ChatLiteLLM
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_elasticsearch import ApproxRetrievalStrategy, ElasticsearchStore
from langchain.schema import Document
from langchain_core.runnables import RunnableLambda, Runnable, chain, RunnablePassthrough, RunnableBranch
from langchain_core.runnables.config import RunnableConfig
from langchain.schema import StrOutputParser, Document
from langchain_core.runnables.base import RunnableEach
from unstructured.partition.auto import partition
from unstructured.chunking.basic import chunk_elements

from core_api.src.publisher_handler import FilePublisher
from redbox.storage import ElasticsearchStorageHandler
from redbox.models import File
from redbox.models.settings import Settings
from redbox.models.file import Metadata, UUID, PersistableModel
from redbox.models.chat import ChatRequest, ChatResponse
from redbox.storage import ElasticsearchStorageHandler
from redbox.llm.prompts.core import _core_redbox_prompt
from redbox.storage.storage_handler import BaseStorageHandler
from redbox.models.file import Chunk, File
from redbox.model_db import SentenceTransformerDB

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client
else:
    S3Client = object

@dataclass
class LocalFile:
    creator_user_uuid: UUID
    filepath: Path


def upload_file(
        storage_handler: BaseStorageHandler, 
        s3: S3Client,
        env: Settings
    ):
    @chain
    def wrapped(local_file: LocalFile) -> File:
        file_uuid = str(uuid4())
        s3.put_object(Bucket=env.bucket_name, Key=str(file_uuid), Body=open(local_file.filepath, 'rb'))
        file = File(uuid=file_uuid, creator_user_uuid=local_file.creator_user_uuid, key=file_uuid, bucket=env.bucket_name)
        storage_handler.write_item(file)
        return file
    return wrapped


def file_chunker(env: Settings, s3_client: S3Client, max_chunk_size: int = 20000):
    @chain
    def wrapped(file: File) -> List[Chunk]:
        authenticated_s3_url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": file.bucket, "Key": file.key},
            ExpiresIn=3600,
        )
        elements = partition(url=authenticated_s3_url, strategy=env.partition_strategy)
        raw_chunks = chunk_elements(
            elements, 
            new_after_n_chars=max_chunk_size, 
            max_characters=max_chunk_size+32
        )
        print(f"Elements chunked")
        return [
            Chunk(
                parent_file_uuid=file.uuid,
                index=i,
                text=raw_chunk.text,
                metadata=Metadata(
                    parent_doc_uuid=file.uuid,
                    page_number=raw_chunk.metadata.page_number,
                    languages=raw_chunk.metadata.languages,
                    link_texts=raw_chunk.metadata.link_texts,
                    link_urls=raw_chunk.metadata.link_urls,
                    links=raw_chunk.metadata.links,
                ),
                creator_user_uuid=file.creator_user_uuid,
            )
            for i, raw_chunk in enumerate(raw_chunks)
        ]
    return wrapped


def local_embedder(model: SentenceTransformerDB):
    @chain
    def wrapped(chunks: List[Chunk]) -> List[Chunk]:
        print(f"Starting Embedding")
        embedded_sentences = model.embed_sentences([c.text for c in chunks])
        for i, c in enumerate(chunks):
            c.embedding = embedded_sentences.data[i].embedding
        return chunks
    return wrapped

def chunk_writer(storage_handler: BaseStorageHandler):
    @chain
    def wrapped(chunks: List[Chunk]) -> UUID:
        print(f"Writing Chunks")
        storage_handler.write_items(chunks)
        return chunks[0].parent_file_uuid
    return wrapped

def make_worker_ingest_runnable(
        storage_handler: BaseStorageHandler,
        s3_client: S3Client,
        env: Settings,
        chunk_size=1024
    ):
    chain =(
        upload_file(storage_handler, s3_client, env)
        | file_chunker(env, s3_client, max_chunk_size=chunk_size)
        | local_embedder(SentenceTransformerDB(embedding_model_name=env.embedding_model))
        | chunk_writer(storage_handler)
    )
    return chain