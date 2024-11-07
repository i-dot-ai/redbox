import pytest

from redbox.models.chain import RedboxState
from redbox.retriever import AllElasticsearchRetriever, MetadataRetriever, ParameterisedElasticsearchRetriever
from redbox.test.data import RedboxChatTestCase

TEST_CHAIN_PARAMETERS = (
    {
        "rag_k": 1,
        "rag_num_candidates": 100,
        "match_boost": 1,
        "knn_boost": 2,
        "similarity_threshold": 0,
        "elbow_filter_enabled": True,
        "rag_gauss_scale_size": 3,
        "rag_gauss_scale_decay": 0.5,
        "rag_gauss_scale_min": 1.1,
        "rag_gauss_scale_max": 2.0,
    },
    {
        "rag_k": 2,
        "rag_num_candidates": 100,
        "match_boost": 1,
        "knn_boost": 2,
        "similarity_threshold": 0,
        "elbow_filter_enabled": False,
        "rag_gauss_scale_size": 1,
        "rag_gauss_scale_decay": 0.1,
        "rag_gauss_scale_min": 1.0,
        "rag_gauss_scale_max": 1.0,
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

    * If documents are selected and there's permission to get them
        * The length of the result is equal to the rag_k parameter
        * The result page content is a subset of all possible correct
        page content
        * The result contains only file_names the user selected
        * The result contains only file_names from permitted S3 keys
    * If documents are selected and there's no permission to get them
        * The length of the result is zero
    * If documents aren't selected and there's permission to get them
        * The length of the result is equal to the rag_k parameter
        * The result page content is a subset of all possible correct
        page content
        * The result contains only file_names from permitted S3 keys
    * If documents aren't selected and there's no permission to get them
        * The length of the result is zero

    Recall that build_retriever_process pays attention to state["text"],
    NOT to state["question"] when choosing what to search with.
    """
    for k, v in chain_params.items():
        setattr(stored_file_parameterised.query.ai_settings, k, v)

    result = parameterised_retriever.invoke(
        RedboxState(request=stored_file_parameterised.query, text=stored_file_parameterised.query.question)
    )
    selected_docs = stored_file_parameterised.get_docs_matching_query()
    permitted_docs = stored_file_parameterised.get_all_permitted_docs()

    selected = bool(stored_file_parameterised.query.s3_keys)
    permission = bool(stored_file_parameterised.query.permitted_s3_keys)

    if not permission:
        assert len(result) == 0
    else:
        assert len(result) == chain_params["rag_k"]
        assert {c.page_content for c in result} <= {c.page_content for c in permitted_docs}
        assert {c.metadata["uri"] for c in result} <= set(stored_file_parameterised.query.permitted_s3_keys)

        if selected:
            assert {c.page_content for c in result} <= {c.page_content for c in selected_docs}
            assert {c.metadata["uri"] for c in result} <= set(stored_file_parameterised.query.s3_keys)


def test_all_chunks_retriever(
    all_chunks_retriever: AllElasticsearchRetriever, stored_file_all_chunks: RedboxChatTestCase
):
    """
    Given a RedboxState, asserts:

    * If documents are selected and there's permission to get them
        * The length of the result is equal to the total stored chunks
        * The result page content is identical to all possible correct
        page content
        * The result contains exactly file_names the user selected
        * The result contains a subset of file_names from permitted S3 keys
    * If documents are selected and there's no permission to get them
        * The length of the result is zero
    * If documents aren't selected and there's permission to get them
        * The length of the result is zero
    * If documents aren't selected and there's no permission to get them
        * The length of the result is zero
    """
    result = all_chunks_retriever.invoke(RedboxState(request=stored_file_all_chunks.query))
    correct = stored_file_all_chunks.get_docs_matching_query()

    selected = bool(stored_file_all_chunks.query.s3_keys)
    permission = bool(stored_file_all_chunks.query.permitted_s3_keys)

    if selected and permission:
        assert len(result) == len(correct)
        assert {c.page_content for c in result} == {c.page_content for c in correct}
        assert {c.metadata["uri"] for c in result} == set(stored_file_all_chunks.query.s3_keys)
        assert {c.metadata["uri"] for c in result} <= set(stored_file_all_chunks.query.permitted_s3_keys)
    else:
        len(result) == 0


def test_metadata_retriever(metadata_retriever: MetadataRetriever, stored_file_metadata: RedboxChatTestCase):
    """
    Given a RedboxState, asserts:

    * If documents are selected and there's permission to get them
        * The length of the result is equal to the total stored chunks
        * The result contains exactly file_names the user selected
        * The result contains a subset of file_names from permitted S3 keys
    * If documents are selected and there's no permission to get them
        * The length of the result is zero
    * If documents aren't selected and there's permission to get them
        * The length of the result is zero
    * If documents aren't selected and there's no permission to get them
        * The length of the result is zero
    """

    result = metadata_retriever.invoke(RedboxState(request=stored_file_metadata.query))
    correct = stored_file_metadata.get_docs_matching_query()

    selected = bool(stored_file_metadata.query.s3_keys)
    permission = bool(stored_file_metadata.query.permitted_s3_keys)

    if selected and permission:
        assert len(result) == len(correct)
        assert {c.metadata["uri"] for c in result} == set(stored_file_metadata.query.s3_keys)
        assert {c.metadata["uri"] for c in result} <= set(stored_file_metadata.query.permitted_s3_keys)
    else:
        len(result) == 0
