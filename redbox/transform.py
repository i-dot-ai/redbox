
from typing import List

from langchain_core.documents.base import Document

from redbox.models.chat import SourceDocument
from redbox.models.file import encoding

def map_document_to_source_document(d: Document) -> SourceDocument:

    def map_page_numbers(page_number: int | List[int]| None) -> List[int]:
        if isinstance(page_number, List):
            return page_number
        elif isinstance(page_number, int):
            return [page_number]
        else:
            return []

    return SourceDocument(
        page_content=d.page_content,
        file_uuid=(d.metadata['_source']['metadata']['parent_file_uuid'] 
            if 'parent_file_uuid' in d.metadata['_source']['metadata']
            else d.metadata['_source']['metadata']["parent_doc_uuid"]),
        page_numbers=map_page_numbers(d.metadata['_source']['metadata'].get('page_number'))
    )

# This should be unnecessary and indicates we're not chunking correctly
def combine_documents(a: Document, b: Document):
    def combine_values(field_name):
        return list(
                filter(lambda x: x is not None, 
                [a.metadata['_source']['metadata'].get(field_name), b.metadata['_source']['metadata'].get(field_name)]
                )
        )

    combined_content = a.page_content + b.page_content
    combined_metadata = a.metadata.copy()
    combined_metadata["token_count"] = len(encoding.encode(combined_content))
    combined_metadata['page_number'] = combine_values("page_number")
    combined_metadata['languages'] = combine_values("languages")
    combined_metadata['link_texts'] = combine_values("link_texts")
    combined_metadata['link_urls'] = combine_values("link_urls")
    combined_metadata['links'] = combine_values("links")
    return Document(
        page_content=combined_content,
        metadata=combined_metadata
    )