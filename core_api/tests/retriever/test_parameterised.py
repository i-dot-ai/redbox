
from typing import List


from langchain_elasticsearch.retrievers import ElasticsearchRetriever
from langchain_core.documents.base import Document

from core_api.src.retriever import ParameterisedElasticsearchRetriever
from redbox.models.file import Chunk, File


def test_parameterised_retriever(parameterised_retriever: ParameterisedElasticsearchRetriever, stored_file_parameterised: List[Document]):
    for k in [1, 2]:
        result = parameterised_retriever.with_config(
            configurable={
                "params": {
                    "size": k,
                    "num_candidates": 100,
                    "match_boost": 1,
                    "knn_boost": 2,
                    "similarity_threshold": 0.7,
                }
            }
        ).invoke({
            "question": "is this real?",
            "file_uuids": [stored_file_parameterised[0].metadata['parent_file_uuid']],
            "user_uuid": stored_file_parameterised[0].metadata['creator_user_uuid']
        })
        assert len(result) == k


def test_parameterised_retriever_legacy_chunks(parameterised_retriever: ElasticsearchRetriever, chunked_file: File):
    for k in [1, 2]:
        result = parameterised_retriever.with_config(
            configurable={
                "params": {
                    "size": k,
                    "num_candidates": 100,
                    "match_boost": 1,
                    "knn_boost": 2,
                    "similarity_threshold": 0.7,
                }
            }
        ).invoke({
            "question": "is this real?",
            "file_uuids": [chunked_file.uuid],
            "user_uuid": chunked_file.creator_user_uuid
        })
        assert len(result) == k