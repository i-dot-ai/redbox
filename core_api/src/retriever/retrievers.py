from functools import partial
from typing import Any

from elasticsearch.helpers import scan
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.embeddings.embeddings import Embeddings
from langchain_elasticsearch.retrievers import ElasticsearchRetriever

from core_api.src.retriever.queries import ESParams, get_all, get_some


def hit_to_doc(hit: dict[str, Any]) -> Document:
    """
    Backwards compatibility for Chunks and Documents.

    Chunks has two metadata fields in top-level: index and parent_file_uuid. This moves them.
    """
    source = hit["_source"]
    c_meta = {"index": source.get("index"), "parent_file_uuid": source.get("index")}
    return Document(
        page_content=source["text"], metadata={k: v for k, v in c_meta.items() if v is not None} | source["metadata"]
    )


class ParameterisedElasticsearchRetriever(ElasticsearchRetriever):
    params: ESParams
    embedding_model: Embeddings

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(body_func=get_some, document_mapper=hit_to_doc, content_field=None, **kwargs)
        self.body_func = partial(get_some, self.embedding_model, self.params)


class AllElasticsearchRetriever(ElasticsearchRetriever):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(body_func=get_all, document_mapper=hit_to_doc, content_field=None, **kwargs)

    def _get_relevant_documents(self, query: str, *, run_manager: CallbackManagerForRetrieverRun) -> list[Document]:  # noqa:ARG002
        if not self.es_client or not self.document_mapper:
            msg = "faulty configuration"
            raise ValueError(msg)  # should not happen

        body = self.body_func(query)

        results = [
            self.document_mapper(hit)
            for hit in scan(client=self.es_client, index=self.index_name, query=body, source=True)
        ]

        return sorted(results, key=lambda result: result.metadata["index"])
