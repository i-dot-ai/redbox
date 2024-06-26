
from functools import lru_cache
from typing import Any


from .base import ESQuery

def get_all_chunks_query(query: ESQuery) -> dict[str, Any]:
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
                        {
                            "terms": {
                                "metadata.parent_file_uuid.keyword": [str(uuid) for uuid in query["file_uuids"]]
                            }
                        },
                    ]
                }
            }
        )
    return {
        "query": {
            "bool" : {
                "must" : {
                    "match_all": {}
                },
                "filter": query_filter
            }
        }
    }