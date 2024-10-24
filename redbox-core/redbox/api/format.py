import json

from langchain_core.documents.base import Document

from redbox.models.chain import ToolState
from redbox.transform import combine_documents


def format_documents(documents: list[Document]) -> str:
    formatted: list[str] = []
    for d in documents:
        doc_xml = (
            f"<Document>\n"
            f"\t<SourceType>{d.metadata.get("creator_type", "Unknown")}</SourceType>\n"
            f"\t<Source>{d.metadata.get("uri", "")}</Source>\n"
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


def format_toolstate(toolstate: ToolState | None) -> str:
    """Takes a toolstate and transforms it into a structure familiar to an LLM."""
    if not toolstate:
        return ""

    formatted_calls: list[str] = []

    for call_info in toolstate.values():
        tool_call = (
            "<ToolCall>\n"
            f"\t<Name>{call_info['tool']['name']}</Name>\n"
            f"\t<Type>{call_info['tool']['type']}</Type>\n"
            f"\t<Called>{str(call_info['called']).lower()}</Called>\n"
            "\t<Arguments>\n"
            f"{json.dumps(call_info['tool']['args'], indent=2).replace('{', '').replace('}', '').replace('"', '')}\n"
            "\t</Arguments>\n"
            "</ToolCall>"
        )
        formatted_calls.append(tool_call)

    return "\n\n".join(formatted_calls)
