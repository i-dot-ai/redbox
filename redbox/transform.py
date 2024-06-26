
from langchain_core.documents.base import Document

from redbox.models.chat import SourceDocument


def map_document_to_source_document(d: Document) -> SourceDocument:
    return SourceDocument(
        page_content=d.page_content,
        file_uuid=(d.metadata['_source']['metadata']['parent_file_uuid'] 
            if 'parent_file_uuid' in d.metadata['_source']['metadata']
            else d.metadata['_source']['metadata']["parent_doc_uuid"]),
        page_numbers=d.metadata['_source']['metadata'].get('page_number', [])
    )