from functools import partial, reduce
from uuid import UUID

from redbox.models.file import Chunk, Metadata
from redbox.storage import ElasticsearchStorageHandler


def format_chunks(chunks: list[Chunk]) -> str:
    formatted: list[str] = []

    for chunk in chunks:
        doc_xml = f"<Doc{chunk.parent_file_uuid}>\n {chunk.text} \n</Doc{chunk.parent_file_uuid}>"
        formatted.append(doc_xml)

    return "\n\n".join(formatted)


def reduce_chunks_by_tokens(chunks: list[Chunk] | None, chunk: Chunk, max_tokens: int) -> list[Chunk]:
    if not chunks:
        return [chunk]

    last_chunk = chunks[-1]

    if chunk.token_count + last_chunk.token_count <= max_tokens:
        chunks[-1] = Chunk(
            parent_file_uuid=last_chunk.parent_file_uuid,
            index=last_chunk.index,
            text=last_chunk.text + chunk.text,
            metadata=Metadata.merge(last_chunk.metadata, chunk.metadata),
            creator_user_uuid=last_chunk.creator_user_uuid,
        )
    else:
        chunk.index = last_chunk.index + 1
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
