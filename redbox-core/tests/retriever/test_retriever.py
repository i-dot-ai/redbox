import pytest

from redbox.models.chain import RedboxState
from redbox.retriever import ParameterisedElasticsearchRetriever, AllElasticsearchRetriever
from redbox.test.data import RedboxChatTestCase

TEST_CHAIN_PARAMETERS = (
    {
        "rag_k": 1,
        "rag_num_candidates": 100,
        "match_boost": 1,
        "knn_boost": 2,
        "similarity_threshold": 0,
        "elbow_filter_enabled": True,
    },
    {
        "rag_k": 2,
        "rag_num_candidates": 100,
        "match_boost": 1,
        "knn_boost": 2,
        "similarity_threshold": 0,
        "elbow_filter_enabled": False,
    },
)


@pytest.mark.parametrize("chain_params", TEST_CHAIN_PARAMETERS)
def test_parameterised_retriever(
    chain_params: dict,
    parameterised_retriever: ParameterisedElasticsearchRetriever,
    stored_file_parameterised: RedboxChatTestCase,
):
    """
    Given a RedboxState, asserts:

    * The length of the result matches the rag_k parameter
    * The result contains only file_names the user selected
    * The result contains only file_names from permitted S3 keys
    """
    for k, v in chain_params.items():
        setattr(stored_file_parameterised.query.ai_settings, k, v)

    result = parameterised_retriever.invoke(RedboxState(request=stored_file_parameterised.query))
    assert len(result) == chain_params["rag_k"], result
    assert {c.metadata["file_name"] for c in result} <= set(stored_file_parameterised.query.s3_keys)
    assert {c.metadata["file_name"] for c in result} <= set(stored_file_parameterised.query.permitted_s3_keys)


def test_all_chunks_retriever(
    all_chunks_retriever: AllElasticsearchRetriever, stored_file_all_chunks: RedboxChatTestCase
):
    """
    Given a RedboxState, asserts:

    * The length of the result matches the true documents that
    match in the index
    * The results have the correct page_content
    * The result contains only file_names the user selected
    * The result contains only file_names from permitted S3 keys
    """
    result = all_chunks_retriever.invoke(RedboxState(request=stored_file_all_chunks.query))

    assert len(result) == len(stored_file_all_chunks.get_docs_matching_query())
    assert {c.page_content for c in result} == {c.page_content for c in stored_file_all_chunks.docs}
    assert {c.metadata["file_name"] for c in result} == set(stored_file_all_chunks.query.s3_keys)
    assert {c.metadata["file_name"] for c in result} <= set(stored_file_all_chunks.query.permitted_s3_keys)
