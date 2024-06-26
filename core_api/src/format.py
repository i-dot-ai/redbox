from langchain_core.documents.base import Document

from redbox.models.file import encoding
from redbox.transform import combine_documents


def format_documents(documents: list[Document]) -> str:
    formatted: list[str] = []
    for d in documents:
        parent_file_uuid = d.metadata.get("parent_file_uuid")  # New Style Ingest
        if not parent_file_uuid:
            parent_file_uuid = d.metadata.get("parent_doc_uuid")  # Old Style Ingest
        doc_xml = f"<Doc{parent_file_uuid}>\n {d.page_content} \n</Doc{parent_file_uuid}>"
        formatted.append(doc_xml)

    return "\n\n".join(formatted)


def reduce_chunks_by_tokens(chunks: list[Document] | None, chunk: Document, max_tokens: int) -> list[Document]:
    if not chunks:
        return [chunk]

    last_chunk = chunks[-1]
    # Backwards compatible with worker which didn't store token_count
    chunk_tokens = chunk.metadata["_source"]["metadata"].get("token_count") or len(encoding.encode(chunk.page_content))
    last_chunk_tokens = last_chunk.metadata["_source"]["metadata"].get("token_count") or len(
        encoding.encode(last_chunk.page_content)
    )
    if chunk_tokens + last_chunk_tokens <= max_tokens:
        chunks[-1] = combine_documents(last_chunk, chunk)
    else:
        chunks.append(chunk)
    return chunks
