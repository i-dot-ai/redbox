from uuid import UUID
from langchain.schema import Document
from redbox.models.file import Metadata
from functools import reduce
from redbox.storage import ElasticsearchStorageHandler


def format_docs(docs: list[Document]) -> str:
    formatted: list[str] = []
    
    for doc in docs:
        doc_xml = f"<document>\n {doc.page_content} \n</document>"
        formatted.append(doc_xml)
    
    return "\n\n".join(formatted)


def get_file_as_documents(
    file_uuid: UUID,
    user_uuid: UUID,
    storage_handler: ElasticsearchStorageHandler,
    max_tokens: int | None = None
) -> list[Document]:
    """Gets a file as LangChain Documents, splitting it by max_tokens."""
    documents: list[Document] = []
    chunks_unsorted = storage_handler.get_file_chunks(parent_file_uuid=file_uuid, user_uuid=user_uuid)
    chunks = sorted(chunks_unsorted, key=lambda x: x.index)

    total_tokens = sum(chunk.token_count for chunk in chunks)
    print(total_tokens)

    token_count: int = 0
    n = max_tokens or float("inf")
    page_content: list[str] = []
    metadata: list[Metadata | None] = []

    for chunk in chunks:
        if token_count + chunk.token_count >= n:
            document = Document(
                page_content=" ".join(page_content),
                metadata=reduce(Metadata.merge, metadata),
            )
            documents.append(document)
            token_count = 0
            page_content = []
            metadata = []

        page_content.append(chunk.text)
        metadata.append(chunk.metadata)
        token_count += chunk.token_count

    if len(page_content) > 0:
        document = Document(
            page_content=" ".join(page_content),
            metadata=reduce(Metadata.merge, metadata),
        )
        documents.append(document)

    return documents
