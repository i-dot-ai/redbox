import tiktoken
from uuid import uuid5, NAMESPACE_DNS

from langchain_core.documents import Document
from langchain_core.callbacks.manager import dispatch_custom_event
from langchain_core.runnables import RunnableLambda

from redbox.models.chat import SourceDocument
from redbox.models.chain import DocumentState, RequestMetadata


def map_document_to_source_document(d: Document) -> SourceDocument:
    def map_page_numbers(page_number: int | list[int] | None) -> list[int]:
        if isinstance(page_number, list):
            return page_number
        elif isinstance(page_number, int):
            return [page_number]
        else:
            return []

    return SourceDocument(
        page_content=d.page_content,
        s3_key=d.metadata["file_name"],
        page_numbers=map_page_numbers(d.metadata.get("page_number")),
    )


# This should be unnecessary and indicates we're not chunking correctly
def combine_documents(a: Document, b: Document):
    def listify(metadata: dict, field_name: str) -> list:
        field_value = metadata.get(field_name)
        if isinstance(field_value, list):
            return field_value
        if field_value is None:
            return []
        return [field_value]

    def sorted_list_or_none(obj: list):
        return sorted(set(obj)) or None

    def combine_values(field_name: str):
        return sorted_list_or_none(listify(a.metadata, field_name) + listify(b.metadata, field_name))

    combined_content = a.page_content + b.page_content
    combined_metadata = a.metadata.copy()
    combined_metadata["token_count"] = a.metadata["token_count"] + b.metadata["token_count"]
    combined_metadata["page_number"] = combine_values("page_number")
    combined_metadata["languages"] = combine_values("languages")
    combined_metadata["link_texts"] = combine_values("link_texts")
    combined_metadata["link_urls"] = combine_values("link_urls")
    combined_metadata["links"] = combine_values("links")

    return Document(page_content=combined_content, metadata=combined_metadata)


def structure_documents(docs: list[Document]) -> DocumentState:
    """Structures a list of documents by a group_uuid and document_uuid.

    The group_uuid is generated deterministically based on the file_name.

    The document_uuid is taken from the Document metadata directly.
    """
    result = {}

    # Group file_name to UUID lookup
    group_file_lookup = {}
    for d in docs:
        file_name = d.metadata["file_name"]
        if file_name not in group_file_lookup:
            group_file_lookup[file_name] = uuid5(NAMESPACE_DNS, file_name)

    # Group documents by their file_name's UUID
    for d in docs:
        group_uuid = group_file_lookup.get(d.metadata["file_name"])
        doc_dict = {d.metadata["uuid"]: d}

        result[group_uuid] = (result.get(group_uuid) or doc_dict) | doc_dict

    return result


def flatten_document_state(documents: DocumentState) -> list[Document]:
    if not documents:
        return []
    return [document for group in documents.values() for document in group.values()]


@RunnableLambda
def to_request_metadata(prompt_response_model: dict):
    """Takes a dictionary with keys 'prompt', 'response' and 'model' and creates metadata.

    Will also emit events for metadata updates.
    """
    model = prompt_response_model["model"]

    try:
        tokeniser = tiktoken.encoding_for_model(model)
    except KeyError:
        tokeniser = tiktoken.get_encoding("cl100k_base")

    input_tokens = {model: len(tokeniser.encode(prompt_response_model["prompt"]))}
    output_tokens = {model: len(tokeniser.encode(prompt_response_model["response"]))}

    dispatch_custom_event("on_metadata_generation", RequestMetadata(input_tokens=input_tokens, output_tokens=dict()))
    dispatch_custom_event("on_metadata_generation", RequestMetadata(input_tokens=dict(), output_tokens=output_tokens))

    return RequestMetadata(input_tokens=input_tokens, output_tokens=output_tokens)
