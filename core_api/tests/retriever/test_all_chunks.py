from langchain_core.documents.base import Document
from langchain_elasticsearch.retrievers import ElasticsearchRetriever

from redbox.models.file import Chunk, File


def test_happy_path(all_chunks_retriever: ElasticsearchRetriever, stored_file_all_chunks: list[Document]):
    result = all_chunks_retriever.invoke(
        {
            "question": "is this real?",
            "file_uuids": [stored_file_all_chunks[0].metadata["parent_file_uuid"]],
            "user_uuid": stored_file_all_chunks[0].metadata["creator_user_uuid"],
        }
    )
    assert len(result) == len(stored_file_all_chunks)
    assert {c.page_content for c in result} == {c.page_content for c in stored_file_all_chunks}


def test_all_chunks_retriever_legacy_chunks(
    all_chunks_retriever: ElasticsearchRetriever, chunked_file: File, stored_file_chunks: list[Chunk]
):
    result = all_chunks_retriever.invoke(
        {"question": "is this real?", "file_uuids": [chunked_file.uuid], "user_uuid": chunked_file.creator_user_uuid}
    )
    assert len(result) == len(stored_file_chunks)
    assert {c.metadata["_id"] for c in result} == {str(c.uuid) for c in stored_file_chunks}
    assert {c.metadata["_source"]["metadata"]["parent_doc_uuid"] for c in result} == {
        c.parent_file_uuid for c in stored_file_chunks
    }
