
from typing import List

from langchain_elasticsearch.retrievers import ElasticsearchRetriever
from langchain_core.documents.base import Document

from redbox.models.file import Chunk, File


def test_happy_path(all_chunks_retriever: ElasticsearchRetriever, stored_file_all_chunks: List[Document]):
    result = all_chunks_retriever.invoke({
        "question": "is this real?",
        "file_uuids": [stored_file_all_chunks[0].metadata['parent_file_uuid']],
        "user_uuid": stored_file_all_chunks[0].metadata['creator_user_uuid']
    })
    assert len(result) == len(stored_file_all_chunks)
    assert set(map(lambda c: c.page_content, result)) == set(map(lambda c: c.page_content, stored_file_all_chunks))


def test_all_chunks_retriever_legacy_chunks(all_chunks_retriever: ElasticsearchRetriever, chunked_file: File, stored_file_chunks: List[Chunk]):
    result = all_chunks_retriever.invoke({
        "question": "is this real?",
        "file_uuids": [chunked_file.uuid],
        "user_uuid": chunked_file.creator_user_uuid
    })
    assert len(result) == len(stored_file_chunks)
    assert set(map(lambda c: c.metadata['_id'], result)) == set(map(lambda c: str(c.uuid), stored_file_chunks))
    assert set(map(lambda c: c.metadata['_source']['metadata']['parent_doc_uuid'], result)) == set(map(lambda c: str(c.parent_file_uuid), stored_file_chunks))
