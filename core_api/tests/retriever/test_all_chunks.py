from langchain_core.documents.base import Document

from core_api.src.retriever import AllElasticsearchRetriever
from redbox.models.file import Chunk, File


def test_all_chunks_retriever(all_chunks_retriever: AllElasticsearchRetriever, stored_file_all_chunks: list[Document]):
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
    all_chunks_retriever: AllElasticsearchRetriever, chunked_file: File, stored_file_chunks: list[Chunk]
):
    result = all_chunks_retriever.invoke(
        {"question": "is this real?", "file_uuids": [chunked_file.uuid], "user_uuid": chunked_file.creator_user_uuid}
    )
    assert len(result) == len(stored_file_chunks)
    assert {c.page_content for c in result} == {c.text for c in stored_file_chunks}
