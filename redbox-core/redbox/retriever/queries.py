import logging
from typing import Any

from langchain_core.documents import Document

from redbox.models.chain import RedboxState, AISettings
from redbox.models.file import ChunkResolution

log = logging.getLogger()


def build_file_filter(file_names: list[str]) -> dict[str, Any]:
    """Creates an Elasticsearch filter for file names."""
    return {"terms": {"metadata.file_name.keyword": file_names}}


def build_resolution_filter(chunk_resolution: ChunkResolution) -> dict[str, Any]:
    """Creates an Elasticsearch filter for chunk resolutions."""
    return {"term": {"metadata.chunk_resolution.keyword": str(chunk_resolution)}}


def build_query_filter(
    selected_files: list[str], permitted_files: list[str], chunk_resolution: ChunkResolution | None
) -> list[dict[str, Any]]:
    """Generic filter constructor for all queries.

    Warns if the selected S3 keys aren't in the permitted S3 keys.
    """
    selected_files = set(selected_files)
    permitted_files = set(permitted_files)

    if not selected_files <= permitted_files:
        log.warning(
            "User has selected files they aren't permitted to access: \n"
            f"{", ".join(selected_files - permitted_files)}"
        )

    file_names = list(selected_files & permitted_files)

    query_filter = []

    query_filter.append(build_file_filter(file_names=file_names))

    if chunk_resolution:
        query_filter.append(build_resolution_filter(chunk_resolution=chunk_resolution))

    return query_filter


def get_all(
    chunk_resolution: ChunkResolution | None,
    state: RedboxState,
) -> dict[str, Any]:
    """
    Returns a parameterised elastic query that will return everything it matches.

    As it's used in summarisation, it excludes embeddings.
    """
    query_filter = build_query_filter(
        selected_files=state["request"].s3_keys,
        permitted_files=state["request"].permitted_s3_keys,
        chunk_resolution=chunk_resolution,
    )

    return {
        "_source": {"excludes": ["*embedding"]},
        "query": {"bool": {"must": {"match_all": {}}, "filter": query_filter}},
    }


def get_metadata(
    chunk_resolution: ChunkResolution | None,
    state: RedboxState,
) -> dict[str, Any]:
    query_filter = build_query_filter(
        selected_files=state["request"].s3_keys,
        permitted_files=state["request"].permitted_s3_keys,
        chunk_resolution=chunk_resolution,
    )

    return {
        "_source": {"excludes": ["*embedding", "text"]},
        "query": {"bool": {"must": {"match_all": {}}, "filter": query_filter}},
    }


def build_document_query(
    query: str,
    query_vector: list[float],
    embedding_field_name: str,
    ai_settings: AISettings,
    permitted_files: list[str],
    selected_files: list[str] | None = None,
    chunk_resolution: ChunkResolution | None = None,
    adjacent: list[Document] | None = None,
) -> dict[str, Any]:
    """Builds a an Elasticsearch query that will return documents when called.

    Searches the document:
        * Text, as a keyword and similarity
        * Name
        * Description
        * Keywords

    If given a list of documents in adjacent, will boost adjacent documents by
    the score of the documents it's been given, scaled.
    """
    # If nothing is selected, consider all permitted files selected
    if not selected_files:
        selected_files = permitted_files

    query_filter = build_query_filter(
        selected_files=selected_files,
        permitted_files=permitted_files,
        chunk_resolution=chunk_resolution,
    )

    query_elastic = {
        "size": ai_settings.rag_k,
        "query": {
            "bool": {
                "should": [
                    {
                        "match": {
                            "text": {
                                "query": query,
                                "boost": ai_settings.match_boost,
                            }
                        },
                    },
                    {
                        "knn": {
                            "field": embedding_field_name,
                            "query_vector": query_vector,
                            "num_candidates": ai_settings.rag_num_candidates,
                            "filter": query_filter,
                            "boost": ai_settings.knn_boost,
                            "similarity": ai_settings.similarity_threshold,
                        }
                    },
                ],
                "filter": query_filter,
            }
        },
    }

    def scale_score(score: float, old_min: float, old_max: float, new_min=1.1, new_max: float = 2.0):
        """Rescales an Elasticsearch score.

        Intended to turn the score into a multiplier to weight a Gauss function.

        If the old range is zero or undefined, returns new_min.
        """
        if old_max == old_min:
            return new_min

        return new_min + (score - old_min) * (new_max - new_min) / (old_max - old_min)

    if adjacent:
        gauss_functions: list[dict[str, Any]] = []
        gauss_scale = 3
        scores = [d.metadata["score"] for d in adjacent]
        old_min = min(scores)
        old_max = max(scores)
        new_min = 1.1
        new_max = 2.0

        for document in adjacent:
            gauss_functions.append(
                {
                    "filter": {"term": {"metadata.file_name.keyword": document.metadata["file_name"]}},
                    "gauss": {
                        "metadata.index": {
                            "origin": document.metadata["index"],
                            "scale": gauss_scale,
                            "offset": 0,
                            "decay": 0.5,
                        }
                    },
                    "weight": scale_score(
                        score=document.metadata["score"],
                        old_min=old_min,
                        old_max=old_max,
                        new_min=new_min,
                        new_max=new_max,
                    ),
                }
            )

        # The size should minimally capture changes to documents either
        # side of every Gauss function applied, including the document
        # itself (double + 1). Of course, this is a ranking, so most of
        # these results will be removed again later
        return {
            "size": query_elastic.get("size") * ((gauss_scale * 2) + 1),
            "query": {
                "function_score": {
                    "query": query_elastic.get("query"),
                    "functions": gauss_functions,
                    "score_mode": "max",
                    "boost_mode": "multiply",
                }
            },
        }

    return query_elastic
