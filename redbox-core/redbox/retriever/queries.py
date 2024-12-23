import logging
from typing import Any


from redbox.models.chain import RedboxState
from redbox.models.file import ChunkResolution

log = logging.getLogger()


#  internal
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

#  internal
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
        selected_files=state.request.s3_keys,
        permitted_files=state.request.permitted_s3_keys,
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
        selected_files=state.request.s3_keys,
        permitted_files=state.request.permitted_s3_keys,
        chunk_resolution=chunk_resolution,
    )

    return {
        "_source": {"excludes": ["*embedding", "text"]},
        "query": {"bool": {"must": {"match_all": {}}, "filter": query_filter}},
    }
