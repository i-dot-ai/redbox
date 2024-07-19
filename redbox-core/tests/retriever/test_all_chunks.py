from langchain_core.documents.base import Document

from redbox.retriever import AllElasticsearchRetriever


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
    assert {c.metadata["parent_file_uuid"] for c in result} == {
        str(c.metadata["parent_file_uuid"]) for c in stored_file_all_chunks
    }
