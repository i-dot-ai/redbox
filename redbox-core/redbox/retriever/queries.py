import logging
from typing import Any

from langchain_core.documents import Document

from redbox.models.chain import AISettings, RedboxState
from redbox.models.file import ChunkResolution

log = logging.getLogger()


def build_file_filter(file_names: list[str]) -> dict[str, Any]:
    """Creates an Elasticsearch filter for file names."""
    return {
        "bool": {
            "should": [
                {"terms": {"metadata.file_name.keyword": file_names}},
                {"terms": {"metadata.uri.keyword": file_names}},
            ]
        }
    }


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
) -> dict[str, Any]:
    """Builds a an Elasticsearch query that will return documents when called.

    Searches the document:
        * Text, as a keyword and similarity
    """
    # If nothing is selected, consider all permitted files selected
    if not selected_files:
        selected_files = permitted_files

    query_filter = build_query_filter(
        selected_files=selected_files,
        permitted_files=permitted_files,
        chunk_resolution=chunk_resolution,
    )

    return {
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
                        "match": {
                            "metadata.name": {
                                "query": query,
                                "boost": ai_settings.match_name_boost,
                            }
                        }
                    },
                    {
                        "match": {
                            "metadata.description": {
                                "query": query,
                                "boost": ai_settings.match_description_boost,
                            }
                        }
                    },
                    {
                        "match": {
                            "metadata.keywords": {
                                "query": query,
                                "boost": ai_settings.match_keywords_boost,
                            }
                        }
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


def add_document_filter_scores_to_query(
    elasticsearch_query: dict[str, Any],
    ai_settings: AISettings,
    centres: list[Document],
) -> dict[str, Any]:
    """
    Adds Gaussian function scores to a query centred on a list of documents.

    This function score will scale the centres' scores into a multiplier, and
    boost the score of documents with an index close to them.

    The result will be that documents with the same file name will have their
    score boosted in proportion to how close their index is to a file in the
    "centres" list.

    For example, if foo.txt index 9 with score 7 was passed in the centres list,
    if foo.txt index 10 would have scored 2, it will now be boosted to score 4.
    """
    gauss_functions: list[dict[str, Any]] = []
    gauss_scale = ai_settings.rag_gauss_scale_size
    gauss_decay = ai_settings.rag_gauss_scale_decay
    scores = [d.metadata["score"] for d in centres]
    old_min = min(scores)
    old_max = max(scores)
    new_min = ai_settings.rag_gauss_scale_min
    new_max = ai_settings.rag_gauss_scale_max

    for document in centres:
        gauss_functions.append(
            {
                "filter": {"term": {"metadata.file_name.keyword": document.metadata["uri"]}},
                "gauss": {
                    "metadata.index": {
                        "origin": document.metadata["index"],
                        "scale": gauss_scale,
                        "offset": 0,
                        "decay": gauss_decay,
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
        "size": elasticsearch_query.get("size") * ((gauss_scale * 2) + 1),
        "query": {
            "function_score": {
                "query": elasticsearch_query.get("query"),
                "functions": gauss_functions,
                "score_mode": "max",
                "boost_mode": "multiply",
            }
        },
    }
