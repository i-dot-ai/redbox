from functools import partial, reduce
from uuid import UUID

from langchain_core.documents.base import Document

from redbox.models.file import Chunk, Metadata, combine_documents
from redbox.storage import ElasticsearchStorageHandler


def format_chunks(chunks: list[Chunk]) -> str:
    formatted: list[str] = []

    for chunk in chunks:
        doc_xml = f"<Doc{chunk.parent_file_uuid}>\n {chunk.text} \n</Doc{chunk.parent_file_uuid}>"
        formatted.append(doc_xml)

    return "\n\n".join(formatted)


def format_documents(documents: list[Document]) -> str:
    formatted: list[str] = []
    for d in documents:
        parent_file_uuid = d.metadata.get('parent_file_uuid') #New Style Ingest
        if not parent_file_uuid:
            parent_file_uuid = d.metadata.get('parent_doc_uuid') #Old Style Ingest
        doc_xml = f"<Doc{parent_file_uuid}>\n {d.page_content} \n</Doc{parent_file_uuid}>"
        formatted.append(doc_xml)

    return "\n\n".join(formatted)


def reduce_chunks_by_tokens(chunks: list[Document] | None, chunk: Document, max_tokens: int) -> list[Document]:
    if not chunks:
        return [chunk]

    last_chunk = chunks[-1]
    if chunk.metadata['token_count'] + last_chunk.metadata['token_count'] <= max_tokens:
        chunks[-1] = combine_documents(last_chunk, chunk)
    else:
        chunks.append(chunk)
    return chunks


def get_file_chunked_to_tokens(
    file_uuid: UUID, user_uuid: UUID, storage_handler: ElasticsearchStorageHandler, max_tokens: int | None = None
) -> list[Chunk]:
    """Gets a file as larger document-sized Chunks, splitting it by max_tokens."""
    n = max_tokens or float("inf")
    chunks_unsorted = storage_handler.get_file_chunks(parent_file_uuid=file_uuid, user_uuid=user_uuid)
    chunks_sorted = sorted(chunks_unsorted, key=lambda x: x.index)

    reduce_chunk_n = partial(reduce_chunks_by_tokens, max_tokens=n)

    return reduce(lambda cs, c: reduce_chunk_n(cs, c), chunks_sorted, [])
