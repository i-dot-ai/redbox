from functools import partial
from typing import Any, TypedDict

from langchain_core.embeddings.embeddings import Embeddings
from langchain_elasticsearch.retrievers import ElasticsearchRetriever

from .base import ESQuery


class ESParams(TypedDict):
    size: int
    num_candidates: int
    match_boost: float
    knn_boost: float
    similarity_threshold: float


def parameterised_body_func(embedding_model: Embeddings, params: ESParams, query: ESQuery) -> dict[str, Any]:
    vector = embedding_model.embed_query(query["question"])

    query_filter = [
        {
            "bool": {
                "should": [
                    {"term": {"creator_user_uuid.keyword": str(query["user_uuid"])}},
                    {"term": {"metadata.creator_user_uuid.keyword": str(query["user_uuid"])}},
                ]
            }
        }
    ]

    if len(query["file_uuids"]) != 0:
        query_filter.append(
            {
                "bool": {
                    "should": [
                        {"terms": {"parent_file_uuid.keyword": [str(uuid) for uuid in query["file_uuids"]]}},
                        {"terms": {"metadata.parent_file_uuid.keyword": [str(uuid) for uuid in query["file_uuids"]]}},
                    ]
                }
            }
        )

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
                            "field": "embedding",
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


class ParameterisedElasticsearchRetriever(ElasticsearchRetriever):
    params: ESParams

    def __init__(self, params: dict, embedding_model: Embeddings, **kwargs: Any) -> None:
        kwargs["params"] = params
        kwargs["body_func"] = parameterised_body_func
        super().__init__(**kwargs)
        self.body_func = partial(parameterised_body_func, embedding_model, self.params)
