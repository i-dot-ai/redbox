import ast
import json
import logging
from collections.abc import Generator
from pathlib import Path
from uuid import UUID

import jsonlines
import pandas as pd
import pytest
from deepeval import assert_test
from deepeval.metrics import (
    AnswerRelevancyMetric,
    ContextualPrecisionMetric,
    ContextualRecallMetric,
    ContextualRelevancyMetric,
    FaithfulnessMetric,
    HallucinationMetric,
)
from deepeval.models.base_model import DeepEvalBaseLLM
from deepeval.test_case import LLMTestCase
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk, scan
from langchain_community.chat_models import ChatLiteLLM
from pydantic import BaseModel

from core_api.src.build_chains import build_retrieval_chain
from core_api.src.dependencies import get_llm, get_parameterised_retriever, get_tokeniser
from redbox.models import Settings
from redbox.models.chain import ChainInput

logging.getLogger("elastic_transport.transport").setLevel(logging.CRITICAL)

ROOT = Path(__file__).parents[2]
DATA = ROOT / "notebooks/evaluation/data/0.2.0"

CSV = DATA / "synthetic/ragas_synthetic_data.csv"
EMBEDDINGS = DATA / "embeddings/all-mpnet-base-v2.jsonl"


class ExperimentData(BaseModel):
    """Test required a versioned CSV of evaluation questions and a pre-embedded index."""

    csv: Path
    embeddings: Path


def clear_index(index: str, es: Elasticsearch) -> None:
    documents = scan(es, index=index, query={"query": {"match_all": {}}})
    bulk_data = [{"_op_type": "delete", "_index": doc["_index"], "_id": doc["_id"]} for doc in documents]
    bulk(es, bulk_data, request_timeout=300)


@pytest.fixture()
def llm(env: Settings) -> ChatLiteLLM:
    return get_llm(env)


@pytest.fixture()
def eval_llm(env: Settings) -> DeepEvalBaseLLM:
    """Creates LLM for evaluating our data.

    Note in its current form this hard-codes the same model for generation
    and evaluation, giving a high risk of overfit in these unit tests.
    This should be changed as soon as possible.
    """

    class ChatLiteLLMDeepEval(DeepEvalBaseLLM):
        def __init__(self, model):
            self.model = model

        def load_model(self):
            return self.model

        def generate(self, prompt: str) -> str:
            chat_model = self.load_model()
            return chat_model.invoke(prompt).content

        async def a_generate(self, prompt: str) -> str:
            chat_model = self.load_model()
            res = await chat_model.ainvoke(prompt)
            return res.content

        def get_model_name(self):
            return "Custom LiteLLM Model"

    return ChatLiteLLMDeepEval(model=get_llm(env))


@pytest.fixture()
def deepeval_test_case(llm: ChatLiteLLM, es_client: Elasticsearch, env: Settings) -> Generator[LLMTestCase, None, None]:
    data = ExperimentData(csv=CSV, embeddings=EMBEDDINGS)
    index_name = data.embeddings.stem

    # Clear embeddings from index (in case previous crash stopped teardown)
    clear_index(index=index_name, es=es_client)

    user_uuids: set[UUID] = set()

    # Load embeddings to index
    with jsonlines.open(data.embeddings, mode="r") as reader:
        for chunk_raw in reader:
            chunk = json.loads(chunk_raw)
            user_uuids.add(UUID(chunk["creator_user_uuid"]))
            es_client.index(
                index=index_name,
                id=chunk["uuid"],
                body=chunk,
            )

    if len(user_uuids) > 1:
        msg = "Embeddings have more than one creator_user_uuid"
        raise ValueError(msg)
    else:
        user_uuid = next(iter(user_uuids))

    # Load incomplete evaluation dataset
    dataset = pd.read_csv(data.csv)

    # Set up retriever and RAG chain
    retriever = get_parameterised_retriever(
        env=env,
        es=es_client,
        index_name=index_name,
    )

    rag_chain = build_retrieval_chain(
        llm=llm,
        retriever=retriever,
        tokeniser=get_tokeniser(),
        env=env,
    )

    # Calculate real outputs and yield test cases one at a time
    for testcase in dataset.itertuples(index=False):
        prompt = ChainInput(
            question=testcase.input,
            file_uuids=[],
            user_uuid=str(user_uuid),
            chat_history=[],
        )
        answer = rag_chain.invoke(input=prompt.model_dump(mode="json"))

        yield LLMTestCase(
            input=testcase.input,
            actual_output=answer["response"],
            expected_output=testcase.expected_output,
            context=ast.literal_eval(testcase.context),
            retrieval_context=[doc.page_content for doc in answer["source_documents"]],
        )

    # Delete embeddings from index
    clear_index(index=index_name, es=es_client)


def test_contextual_precision(deepeval_test_case, eval_llm) -> None:
    """Are relevant retrieval_context nodes ranked higher than irrelevant?

    Retrieval metric. Higher is better.

    https://docs.confident-ai.com/docs/metrics-contextual-precision
    """
    contextual_precision = ContextualPrecisionMetric(
        threshold=0.5,  # default is 0.5
        model=eval_llm,
        include_reason=True,
    )
    assert_test(deepeval_test_case, [contextual_precision])


def test_contextual_recall(deepeval_test_case, eval_llm) -> None:
    """How much does retrieval_context align with expected_output?

    Retrieval metric. Higher is better.

    https://docs.confident-ai.com/docs/metrics-contextual-recall
    """
    contextual_recall = ContextualRecallMetric(
        threshold=0.5,  # default is 0.5
        model=eval_llm,
        include_reason=True,
    )
    assert_test(deepeval_test_case, [contextual_recall])


def test_contextual_relevancy(deepeval_test_case, eval_llm) -> None:
    """How relevant is the retrieval_context to the input?

    Retrieval metric. Higher is better.

    https://docs.confident-ai.com/docs/metrics-contextual-relevancy
    """
    contextual_relevancy = ContextualRelevancyMetric(
        threshold=0.5,  # default is 0.5
        model=eval_llm,
        include_reason=True,
    )
    assert_test(deepeval_test_case, [contextual_relevancy])


def test_answer_relevancy(deepeval_test_case, eval_llm) -> None:
    """How relevant is the actual_answer to the input?

    Generation metric. Higher is better.

    https://docs.confident-ai.com/docs/metrics-answer-relevancy
    """
    answer_relevancy = AnswerRelevancyMetric(
        threshold=0.5,  # default is 0.5
        model=eval_llm,
        include_reason=True,
    )
    assert_test(deepeval_test_case, [answer_relevancy])


def test_faithfulness(deepeval_test_case, eval_llm) -> None:
    """How factually faithful is the actual_output to the retrieval_context?

    Generation metric. Higher is better.

    https://docs.confident-ai.com/docs/metrics-faithfulness
    """
    faithfulness = FaithfulnessMetric(
        threshold=0.5,  # default is 0.5
        model=eval_llm,
        include_reason=True,
    )
    assert_test(deepeval_test_case, [faithfulness])


def test_hallucination(deepeval_test_case, eval_llm) -> None:
    """How factually accurate is the output, comparing actual_output to context?

    Generation metric. Lower is better.

    https://docs.confident-ai.com/docs/metrics-hallucination
    """
    hallucination = HallucinationMetric(
        threshold=0.5,  # default is 0.5
        model=eval_llm,
        include_reason=True,
    )
    assert_test(deepeval_test_case, [hallucination])
