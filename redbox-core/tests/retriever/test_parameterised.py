import pytest

from redbox.models.chain import ChainState
from redbox.retriever import ParameterisedElasticsearchRetriever
from tests.data import RedboxChatTestCase

test_chain_parameters = (
    {
        "size": 1,
        "num_candidates": 100,
        "match_boost": 1,
        "knn_boost": 2,
        "similarity_threshold": 0,
    },
    {
        "size": 2,
        "num_candidates": 100,
        "match_boost": 1,
        "knn_boost": 2,
        "similarity_threshold": 0,
    },
)


@pytest.mark.parametrize("chain_params", test_chain_parameters)
def test_parameterised_retriever(
    chain_params,
    parameterised_retriever: ParameterisedElasticsearchRetriever,
    stored_file_parameterised: RedboxChatTestCase,
):
    result = parameterised_retriever.with_config(configurable={"params": chain_params}).invoke(
        ChainState(query=stored_file_parameterised.query)
    )
    assert len(result) == chain_params["size"], result
