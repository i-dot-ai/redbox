import itertools
from typing import Iterable
from uuid import NAMESPACE_DNS, UUID, uuid5

import tiktoken
from langchain_core.callbacks.manager import dispatch_custom_event
from langchain_core.documents import Document
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from redbox.models.chain import DocumentState, LLMCallMetadata, RedboxState, RequestMetadata, DocumentMapping
from redbox.models.graph import RedboxEventType


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


def to_document_mapping(docs: list[Document]) -> DocumentMapping:
    return {doc.metadata["uuid"]: doc for doc in docs}


def group_documents(docs: Iterable[Document]) -> dict[str, list[Document]]:
    def get_uri(d):
        return d.metadata["uri"]

    grouped_docs = itertools.groupby(sorted(docs, key=get_uri), key=get_uri)
    return {key: list(values) for key, values in grouped_docs}


def structure_documents_by_file_name(docs: list[Document]) -> DocumentState:
    """Structures a list of documents by a group_uuid and document_uuid.

    The group_uuid is generated deterministically based on the file_name.

    The document_uuid is taken from the Document metadata directly.
    """
    result = DocumentState()

    grouped_docs = group_documents(docs)

    result.groups = {uuid5(NAMESPACE_DNS, uri): to_document_mapping(d) for uri, d in grouped_docs.items()}

    return result


def create_group_uuid(file_name: str, indices: list[int]) -> UUID:
    """Uses a file name and list of indices to generate a deterministic UUID."""
    unique_str = file_name + "-" + ",".join(map(str, sorted(indices)))
    return uuid5(NAMESPACE_DNS, unique_str)


def create_group_uuid_for_group(documents: list[Document]) -> UUID:
    """create a uuid for a DocumentGroup"""
    if not documents:
        raise ValueError("at least one document is required")

    file_name = documents[0].metadata["uri"]
    group_indices = [d.metadata["index"] for d in documents]
    return create_group_uuid(file_name, group_indices)


def documents_are_consecutive(first: Document, second: Document) -> bool:
    """are the two documents consecutive, i.e. do they appear next to each other in the original text?"""
    if first.metadata["uri"] is None:
        return True

    if first.metadata["uri"] != second.metadata["uri"]:
        return False

    return abs(first.metadata["index"] - second.metadata["index"]) <= 1


def group_and_sort_documents(group: list[Document]) -> list[list[Document]]:
    """Breaks a group into blocks of ordered consecutive indices.

    The group is intended to be a single file_name.
    """
    if not group:
        return []

    # Process consecutive blocks and sort them by index
    consecutive_blocks = []
    temp_block = [group[0]]

    for doc in group[1:]:
        if documents_are_consecutive(temp_block[-1], doc):
            temp_block.append(doc)
        else:
            # Append the current block
            consecutive_blocks.append(temp_block)
            temp_block = [doc]

    # Append the last block
    consecutive_blocks.append(temp_block)

    # Sort each block by index
    sorted_blocks = [sorted(block, key=lambda d: d.metadata["index"]) for block in consecutive_blocks]

    return sorted_blocks


def structure_documents_by_group_and_indices(docs: list[Document]) -> DocumentState:
    """Structures a list of documents by blocks of consecutive indices in group_uuids.

    Assumes a sorted list was passed where blocks of group_uuids with consecutive
    indices are already together, as per redbox.transform.sort_documents().

    The group_uuid is generated deterministically based on the file_name and group indices.

    The document_uuid is taken from the Document metadata directly.
    """
    result = DocumentState()

    groups = group_and_sort_documents(docs)

    result.groups = {
        create_group_uuid_for_group(group): {doc.metadata["uuid"]: doc for doc in group} for group in groups
    }

    return result


def flatten_document_state(documents: DocumentState | None) -> list[Document]:
    """Flattens a DocumentState into a list of Documents."""
    if not documents:
        return []
    return [document for group in documents.groups.values() for document in group.values()]


def get_document_token_count(state: RedboxState) -> int:
    """Calculates the total token count of all documents in a state."""
    return sum(d.metadata["token_count"] for d in flatten_document_state(state.documents))


def to_request_metadata(obj: dict) -> RequestMetadata:
    """Takes a dictionary with keys 'prompt', 'response' and 'model' and creates metadata.

    Will also emit events for metadata updates.
    """

    prompt = obj["prompt"]
    response = obj["text_and_tools"]["raw_response"].content
    model = obj["model"]

    try:
        tokeniser = tiktoken.encoding_for_model(model)
    except KeyError:
        tokeniser = tiktoken.get_encoding("cl100k_base")

    input_tokens = len(tokeniser.encode(prompt))
    output_tokens = len(tokeniser.encode(response))

    metadata_event = RequestMetadata(
        llm_calls=[
            LLMCallMetadata(
                llm_model_name=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
        ]
    )

    dispatch_custom_event(RedboxEventType.on_metadata_generation.value, metadata_event)

    return metadata_event


@RunnableLambda
def get_all_metadata(obj: dict):
    text_and_tools = obj["text_and_tools"]

    if parsed_response := text_and_tools.get("parsed_response"):
        text = getattr(parsed_response, "answer", parsed_response)
        citations = getattr(parsed_response, "citations", [])
    else:
        text = text_and_tools["raw_response"].content
        citations = []

    out = {
        "messages": [AIMessage(content=text, tool_calls=text_and_tools["raw_response"].tool_calls)],
        "metadata": to_request_metadata(obj),
        "citations": citations,
    }
    return out


def merge_documents(initial: list[Document], adjacent: list[Document]) -> list[Document]:
    """Merges a list of adjacent documents with an initial list.

    Privileges the initial score.
    """
    # Keep initial scores
    merged_dict = to_document_mapping(adjacent) | to_document_mapping(initial)

    return sorted(list(merged_dict.values()), key=lambda d: -d.metadata["score"])[: len(initial)]


def sort_documents(documents: list[Document]) -> list[Document]:
    """Sorts a list of documents so chunks are both consecutive and ordered by score.

    More explicitly:

    * Blocks of documents from the same file with consecutive indices are presented together, in order of ascending index
    * Blocks of documents are presented in order of their highest-scoring member

    For example, in this list of (score, file, index):

    5, foo.txt, 3
    4.9, foo.txt, 2
    4.8, bar.txt, 9
    4.1, foo.txt, 1
    3.8, foo.txt, 24

    We will get:

    4.1, foo.txt, 1
    4.9, foo.txt, 2
    5, foo.txt, 3
    4.8, bar.txt, 9
    3.8, foo.txt, 24
    """

    def max_score(group: list[Document]) -> float:
        """Returns the maximum score in a group of documents."""
        return max(d.metadata["score"] for d in group)

    # Group and sort docs by file_name and handle consecutive indices
    grouped_by_file = group_documents(documents)

    # Step 1: group & sort each group
    document_blocks = [group_and_sort_documents(docs) for docs in grouped_by_file.values()]

    # Step 2: flatten blocks into a single list of docs
    all_sorted_blocks = itertools.chain(*document_blocks)

    # Step 3: Sort the blocks by the maximum score within each block
    all_sorted_blocks_by_max_score = sorted(all_sorted_blocks, key=max_score, reverse=True)

    # Step 4: Flatten the list of blocks back into a single list
    return list(itertools.chain.from_iterable(all_sorted_blocks_by_max_score))
