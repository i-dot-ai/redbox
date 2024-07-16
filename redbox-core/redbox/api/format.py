from langchain_core.documents.base import Document

from redbox.models.file import encoding
from redbox.transform import combine_documents


def format_documents(documents: list[Document]) -> str:
    formatted: list[str] = []
    for d in documents:
        parent_file_uuid = d.metadata.get("parent_file_uuid")  # New Style Ingest
        if not parent_file_uuid:
            parent_file_uuid = d.metadata.get("parent_doc_uuid")  # Old Style Ingest

        doc_xml = (
            f"<Document>\n"
            f"\t<UUID>{parent_file_uuid}</UUID>\n"
            f"\t<Filename>{d.metadata.get("file_name", "")}</Filename>\n"
            "\t<Content>\n"
            f"{d.page_content}\n"
            "\t</Content>\n"
            f"</Document>"
        )
        formatted.append(doc_xml)

    return "\n\n".join(formatted)


def reduce_chunks_by_tokens(chunks: list[Document] | None, chunk: Document, max_tokens: int) -> list[Document]:
    if not chunks:
        return [chunk]

    # Backwards compatible with worker which didn't store token_count
    # Everything is optional None so we have to check everything
    # This will all be rolled up into a SummarisationChunkRetriever or similar in future work and this ugliness
    # will all be gone
    def get_chunk_tokens(d: Document):
        return d.metadata.get("token_count", len(encoding.encode(d.page_content)))

    last_chunk = chunks[-1]

    chunk_tokens = get_chunk_tokens(chunk)
    last_chunk_tokens = get_chunk_tokens(last_chunk)
    if chunk_tokens + last_chunk_tokens <= max_tokens:
        chunks[-1] = combine_documents(last_chunk, chunk)
    else:
        chunks.append(chunk)
    return chunks
