from functools import partial
from typing import Any, Callable

from elasticsearch import Elasticsearch
from elasticsearch.helpers import scan
from kneed import KneeLocator
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_elasticsearch.retrievers import ElasticsearchRetriever

from redbox.models.chain import RedboxState
from redbox.models.file import ChunkResolution
from redbox.retriever.queries import get_all, get_metadata


def hit_to_doc(hit: dict[str, Any]) -> Document:
    """
    Backwards compatibility for Chunks and Documents.

    Chunks has two metadata fields in top-level: index and file_name. This moves them.
    """
    source = hit["_source"]
    c_meta = {
        "index": source.get("index"),
        "uri": source["metadata"].get(
            "uri", source["metadata"].get("file_name")
        ),  # Handle mapping previously ingested documents
        "score": hit["_score"],
        "uuid": hit["_id"],
    }
    return Document(
        page_content=source.get("text", ""),
        metadata={k: v for k, v in c_meta.items() if v is not None} | source["metadata"],
    )


def query_to_documents(es_client: Elasticsearch, index_name: str, query: dict[str, Any]) -> list[Document]:
    """Runs an Elasticsearch query and returns Documents."""
    response = es_client.search(index=index_name, body=query)
    return [hit_to_doc(hit) for hit in response["hits"]["hits"]]


def filter_by_elbow(
    enabled: bool = True, sensitivity: float = 1, score_scaling_factor: float = 100
) -> Callable[[list[Document]], list[Document]]:
    """Filters a list of documents by the elbow point on the curve of their scores.

    Args:
        enabled (bool, optional): Whether to enable the filter. Defaults to True.
    Returns:
        callable: A function that takes a list of documents and returns a list of documents.
    """

    def _filter_by_elbow(docs: list[Document]) -> list[Document]:
        # If enabled, return only the documents up to the elbow point
        if enabled:
            if len(docs) == 0:
                return docs

            # *scaling because algorithm performs poorly on changes of ~1.0
            try:
                scores = [doc.metadata["score"] * score_scaling_factor for doc in docs]
            except AttributeError as exc:
                raise exc

            rank = range(len(scores))

            # Convex curve, decreasing direction as scores descend in a pareto-like fashion
            kn = KneeLocator(rank, scores, S=sensitivity, curve="convex", direction="decreasing")
            return docs[: kn.elbow]
        else:
            return docs

    return _filter_by_elbow


class AllElasticsearchRetriever(ElasticsearchRetriever):
    """A modified ElasticsearchRetriever that allows retrieving whole documents."""

    chunk_resolution: ChunkResolution = ChunkResolution.largest

    def __init__(self, **kwargs: Any) -> None:
        # Hack to pass validation before overwrite
        # Partly necessary due to how .with_config() interacts with a retriever
        kwargs["body_func"] = get_all
        kwargs["document_mapper"] = hit_to_doc
        super().__init__(**kwargs)
        self.body_func = partial(get_all, self.chunk_resolution)

    def _get_relevant_documents(
        self, query: RedboxState, *, run_manager: CallbackManagerForRetrieverRun
    ) -> list[Document]:  # noqa:ARG002
        if not self.es_client or not self.document_mapper:
            msg = "faulty configuration"
            raise ValueError(msg)  # should not happen

        body = self.body_func(query)  # type: ignore

        results = [
            self.document_mapper(hit)
            for hit in scan(client=self.es_client, index=self.index_name, query=body, source=True)
        ]

        return sorted(results, key=lambda result: result.metadata["index"])


class MetadataRetriever(ElasticsearchRetriever):
    """A modified ElasticsearchRetriever that retrieves query metadata without any content"""

    chunk_resolution: ChunkResolution = ChunkResolution.largest

    def __init__(self, **kwargs: Any) -> None:
        # Hack to pass validation before overwrite
        # Partly necessary due to how .with_config() interacts with a retriever
        kwargs["body_func"] = get_metadata
        kwargs["document_mapper"] = hit_to_doc
        super().__init__(**kwargs)
        self.body_func = partial(get_metadata, self.chunk_resolution)

    def _get_relevant_documents(
        self, query: RedboxState, *, run_manager: CallbackManagerForRetrieverRun
    ) -> list[Document]:  # noqa:ARG002
        if not self.es_client or not self.document_mapper:
            msg = "faulty configuration"
            raise ValueError(msg)  # should not happen

        body = self.body_func(query)  # type: ignore

        results = [
            self.document_mapper(hit)
            for hit in scan(client=self.es_client, index=self.index_name, query=body, source=True)
        ]

        return sorted(results, key=lambda result: result.metadata["index"])
