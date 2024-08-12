from typing import Any, TypedDict
from uuid import UUID

from langchain_core.embeddings.embeddings import Embeddings

from redbox.models.file import ChunkResolution


class ESQuery(TypedDict):
    question: str
    file_uuids: list[UUID]
    user_uuid: UUID


class ESParams(TypedDict):
    size: int
    num_candidates: int
    match_boost: float
    knn_boost: float
    similarity_threshold: float


def make_query_filter(user_uuid: UUID, file_uuids: list[UUID], chunk_resolution: ChunkResolution | None) -> list[dict]:
    query_filter: list[dict] = [
        {
            "bool": {
                "should": [
                    {"term": {"creator_user_uuid.keyword": str(user_uuid)}},
                    {"term": {"metadata.creator_user_uuid.keyword": str(user_uuid)}},
                ]
            }
        }
    ]

    if len(file_uuids) != 0:
        query_filter.append(
            {
                "bool": {
                    "should": [
                        {"terms": {"parent_file_uuid.keyword": [str(uuid) for uuid in file_uuids]}},
                        {"terms": {"metadata.parent_file_uuid.keyword": [str(uuid) for uuid in file_uuids]}},
                    ]
                }
            }
        )

    if chunk_resolution:
        query_filter.append(
            {
                "bool": {
                    "must": [
                        {"term": {"metadata.chunk_resolution.keyword": str(chunk_resolution)}},
                    ]
                }
            }
        )
    return query_filter


def get_all(
    chunk_resolution: ChunkResolution | None,
    query: ESQuery,
) -> dict[str, Any]:
    """
    Returns a parameterised elastic query that will return everything it matches.

    As it's used in summarisation, it excludes embeddings.
    """

    query_filter = make_query_filter(query["user_uuid"], query["file_uuids"], chunk_resolution)
    return {
        "_source": {"excludes": ["*embedding"]},
        "query": {"bool": {"must": {"match_all": {}}, "filter": query_filter}},
    }


def get_some(
    embedding_model: Embeddings,
    params: ESParams,
    embedding_field_name: str,
    chunk_resolution: ChunkResolution | None,
    query: ESQuery,
) -> dict[str, Any]:
    vector = embedding_model.embed_query(query["question"])

    query_filter = make_query_filter(query["user_uuid"], query["file_uuids"], chunk_resolution)

    return {
        "size": params["size"],
        "query": {
            "bool": {
                "should": [
                    {
                        "match": {
                            "text": {
                                "query": query["question"],
                                "boost": params["match_boost"],
                            }
                        }
                    },
                    {
                        "knn": {
                            "field": embedding_field_name,
                            "query_vector": vector,
                            "num_candidates": params["num_candidates"],
                            "filter": query_filter,
                            "boost": params["knn_boost"],
                            "similarity": params["similarity_threshold"],
                        }
                    },
                ],
                "filter": query_filter,
            }
        },
    }
