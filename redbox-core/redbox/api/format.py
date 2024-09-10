from langchain_core.documents.base import Document

from redbox.transform import combine_documents


def format_documents(documents: list[Document]) -> str:
    formatted: list[str] = []
    for d in documents:
        doc_xml = (
            f"<Document>\n"
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

    last_chunk = chunks[-1]

    chunk_tokens = chunk.metadata["token_count"]
    last_chunk_tokens = last_chunk.metadata["token_count"]
    if chunk_tokens + last_chunk_tokens <= max_tokens:
        chunks[-1] = combine_documents(last_chunk, chunk)
    else:
        chunks.append(chunk)
    return chunks
