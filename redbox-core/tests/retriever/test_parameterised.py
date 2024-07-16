import pytest
from langchain_core.documents.base import Document
from langchain_elasticsearch.retrievers import ElasticsearchRetriever

from redbox.retriever import ParameterisedElasticsearchRetriever
from redbox.models.file import File

test_chain_parameters = (
    {
        "size": 1,
        "num_candidates": 100,
        "match_boost": 1,
        "knn_boost": 2,
        "similarity_threshold": 0.7,
    },
    {
        "size": 2,
        "num_candidates": 100,
        "match_boost": 1,
        "knn_boost": 2,
        "similarity_threshold": 0.7,
    },
)


@pytest.mark.parametrize("chain_params", test_chain_parameters)
def test_parameterised_retriever(
    chain_params,
    parameterised_retriever: ParameterisedElasticsearchRetriever,
    stored_file_parameterised: list[Document],
):
    result = parameterised_retriever.with_config(configurable={"params": chain_params}).invoke(
        {
            "question": "is this real?",
            "file_uuids": [stored_file_parameterised[0].metadata["parent_file_uuid"]],
            "user_uuid": stored_file_parameterised[0].metadata["creator_user_uuid"],
        }
    )
    assert len(result) == chain_params["size"], result
