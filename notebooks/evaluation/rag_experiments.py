import json
import sys
from dataclasses import asdict
from operator import itemgetter
from pathlib import Path
from typing import Annotated
from uuid import UUID

import click
import jsonlines
import pandas as pd
import seaborn as sns
from deepeval import evaluate
from deepeval.dataset import EvaluationDataset
from deepeval.metrics import (
    AnswerRelevancyMetric,
    ContextualPrecisionMetric,
    ContextualRecallMetric,
    ContextualRelevancyMetric,
    FaithfulnessMetric,
    HallucinationMetric,
)
from dotenv import find_dotenv, load_dotenv
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk, scan
from fastapi import Depends
from langchain.globals import set_verbose
from langchain.schema import StrOutputParser
from langchain_community.chat_models import ChatLiteLLM
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import ConfigurableField, Runnable, RunnableLambda, RunnablePassthrough
from langchain_core.vectorstores import VectorStoreRetriever
from scipy import stats
from tiktoken import Encoding

sys.path.append(str(Path(__file__).parents[2]))
from core_api.src import dependencies
from core_api.src.dependencies import get_tokeniser
from core_api.src.format import format_documents
from core_api.src.retriever import ParameterisedElasticsearchRetriever
from core_api.src.runnables import make_chat_prompt_from_messages_runnable
from redbox.models import ChatRoute, Settings
from redbox.models.chain import ChainInput
from redbox.models.file import UUID
from redbox.models.settings import ElasticLocalSettings

set_verbose(False)


_ = load_dotenv(find_dotenv())


class GetExperimentResults:
    def __init__(self):
        self.data_version = None
        self.benchmark = None
        self.V_EMBEDDINGS = ""
        self.V_ROOT = None
        self.V_SYNTHETIC = None
        self.V_RESULTS = None
        self.MODEL = None
        self.ES_CLIENT = None
        self.INDEX = None
        self.experiment_name = None
        self.retrieval_system_prompt = None
        self.retrieval_question_prompt = None
        self.eval_results = None
        self.ENV = Settings(minio_host="localhost", elastic=ElasticLocalSettings(host="localhost"))
        self.LLM = ChatLiteLLM(
            model="gpt-4o",
            streaming=True,
        )
        self.FILE_UUIDS = None
        self.USER_UUID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        self.experiment_file_name = None
        self.experiment_parameters = None

    def set_data_version(self, data_version):
        self.data_version = data_version
        ROOT = Path(__file__).parents[2]
        EVALUATION_DIR = ROOT / "notebooks/evaluation"
        self.V_ROOT = EVALUATION_DIR / f"data/{self.data_version}"  # UNSURE ATM
        self.V_SYNTHETIC = self.V_ROOT / "synthetic"
        self.V_RESULTS = self.V_ROOT / "results"
        self.V_EMBEDDINGS = self.V_ROOT / "embeddings"
        self.MODEL = self.ENV.embedding_model
        self.INDEX = f"{self.data_version}-{self.MODEL}".lower()
        self.ES_CLIENT = self.ENV.elasticsearch_client()

    def load_chunks_from_jsonl_to_index(self) -> set:
        file_uuids = set()
        file_path = self.V_EMBEDDINGS / f"{self.MODEL}.jsonl"

        with jsonlines.open(file_path, mode="r") as reader:
            for chunk_raw in reader:
                chunk = json.loads(chunk_raw)
                self.ES_CLIENT.index(
                    index=self.INDEX,
                    id=chunk["uuid"],
                    body=chunk,
                )

                file_uuids.add(chunk["parent_file_uuid"])
        self.FILE_UUIDS = file_uuids
        return file_uuids

    def clear_index(self) -> None:
        if self.ES_CLIENT.indices.exists(index=self.INDEX):
            documents = scan(self.ES_CLIENT, index=self.INDEX, query={"query": {"match_all": {}}})
            bulk_data = [{"_op_type": "delete", "_index": doc["_index"], "_id": doc["_id"]} for doc in documents]
            bulk(self.ES_CLIENT, bulk_data, request_timeout=300)

    def get_parameterised_retriever(
        self, es: Annotated[Elasticsearch, Depends(dependencies.get_elasticsearch_client)]
    ) -> BaseRetriever:
        """Creates an Elasticsearch retriever runnable.

        Runnable takes input of a dict keyed to question, file_uuids and user_uuid.

        Runnable returns a list of Chunks.
        """
        default_params = {
            "size": self.ENV.ai.rag_k,
            "num_candidates": self.ENV.ai.rag_num_candidates,
            "match_boost": 1,
            "knn_boost": 1,
            "similarity_threshold": 0,
        }

        return ParameterisedElasticsearchRetriever(
            es_client=es,
            index_name=self.INDEX,
            params=default_params,
            embedding_model=dependencies.get_embedding_model(self.ENV),
        ).configurable_fields(
            params=ConfigurableField(
                id="params",
                name="Retriever parameters",
                description="A dictionary of parameters to use for the retriever.",
            )
        )

    def build_retrieval_chain(
        self,
        llm: Annotated[ChatLiteLLM, Depends(dependencies.get_llm)],  # llm versus self.LLM
        retriever: Annotated[VectorStoreRetriever, Depends(dependencies.get_parameterised_retriever)],
        tokeniser: Annotated[Encoding, Depends(dependencies.get_tokeniser)],
        env: Annotated[Settings, Depends(dependencies.get_env)],  # get_env versus self.ENV is same-ish thing. PROBLEM
    ) -> Runnable:
        return (
            RunnablePassthrough.assign(documents=retriever)
            | RunnablePassthrough.assign(
                formatted_documents=(RunnablePassthrough() | itemgetter("documents") | format_documents)
            )
            | {
                "response": make_chat_prompt_from_messages_runnable(
                    system_prompt=str(self.retrieval_system_prompt),
                    question_prompt=str(self.retrieval_question_prompt),
                    input_token_budget=env.ai.context_window_size - env.llm_max_tokens,
                    tokeniser=tokeniser,
                )
                | llm
                | StrOutputParser(),
                "source_documents": itemgetter("documents"),
                "route_name": RunnableLambda(lambda _: ChatRoute.search.value),
            }
        )

    def get_rag_results(
        self,
        question,
    ) -> dict:
        """Get Redbox response for a given question."""

        retriever = self.get_parameterised_retriever(es=self.ES_CLIENT)

        chain = self.build_retrieval_chain(llm=self.LLM, retriever=retriever, tokeniser=get_tokeniser(), env=self.ENV)

        response = chain.invoke(
            input=ChainInput(
                question=question,
                chat_history=[{"text": "", "role": "user"}],
                file_uuids=list(self.FILE_UUIDS),
                user_uuid=self.USER_UUID,
            ).model_dump()
        )

        filtered_chunks = []

        for chunk in response["source_documents"]:
            chunk = dict(chunk)
            filtered_chunk = {
                "page_content": chunk["page_content"],
                "page_number": chunk["metadata"]["page_number"],
                "parent_file_uuid": chunk["metadata"]["parent_file_uuid"],
            }
            filtered_chunks.append(filtered_chunk)

        return {"output_text": response["response"], "source_documents": filtered_chunks}

    def write_rag_results(self) -> None:
        """Format and write Redbox responses to evaluation dataset."""

        synthetic_df = pd.read_csv(f"{self.V_SYNTHETIC}/ragas_synthetic_data.csv")
        inputs = synthetic_df["input"].tolist()

        df_function = synthetic_df.copy()

        actual_output = []
        retrieval_context = []

        for question in inputs:
            data = self.get_rag_results(question=question)
            actual_output.append(data["output_text"])
            retrieval_context.append(data["source_documents"])

        df_function["actual_output"] = actual_output
        df_function["retrieval_context"] = retrieval_context

        df_function_clean = df_function.dropna()
        df_function_clean.to_csv(
            f"{self.V_SYNTHETIC}/{self.experiment_name}_complete_ragas_synthetic_data.csv", index=False
        )

    def do_evaluation(self) -> None:
        """
        Calculate evaluation metrics for a synthetic RAGAS dataset, aggregate results
        and write as CSV.
        """

        dataset = EvaluationDataset()
        dataset.add_test_cases_from_csv_file(
            file_path=f"{self.V_SYNTHETIC}/{self.experiment_name}_complete_ragas_synthetic_data.csv",
            input_col_name="input",
            actual_output_col_name="actual_output",
            expected_output_col_name="expected_output",
            context_col_name="context",
            context_col_delimiter=";",
            retrieval_context_col_name="retrieval_context",
            retrieval_context_col_delimiter=";",
        )

        # Instantiate retrieval metrics
        contextual_precision = ContextualPrecisionMetric(
            threshold=0.5,  # default is 0.5
            model="gpt-4o",
            include_reason=True,
        )

        contextual_recall = ContextualRecallMetric(
            threshold=0.5,  # default is 0.5
            model="gpt-4o",
            include_reason=True,
        )

        contextual_relevancy = ContextualRelevancyMetric(
            threshold=0.5,  # default is 0.5
            model="gpt-4o",
            include_reason=True,
        )

        # Instantiate generation metrics
        answer_relevancy = AnswerRelevancyMetric(
            threshold=0.5,  # default is 0.5
            model="gpt-4o",
            include_reason=True,
        )

        faithfulness = FaithfulnessMetric(
            threshold=0.5,  # default is 0.5
            model="gpt-4o",
            include_reason=True,
        )

        hallucination = HallucinationMetric(
            threshold=0.5,  # default is 0.5
            model="gpt-4o",
            include_reason=True,
        )

        self.eval_results = evaluate(
            test_cases=dataset,
            metrics=[
                contextual_precision,
                contextual_recall,
                contextual_relevancy,
                answer_relevancy,
                faithfulness,
                hallucination,
            ],
        )

    def write_evaluation_results(self) -> None:
        metric_type = {
            "metric_name": [
                "Contextual Precision",
                "Contextual Recall",
                "Contextual Relevancy",
                "Answer Relevancy",
                "Faithfulness",
                "Hallucination",
            ],
            "metric_type": ["retrieval", "retrieval", "retrieval", "generation", "generation", "generation"],
        }

        evaluation = (
            pd.DataFrame.from_records(asdict(result) for result in self.eval_results)
            .explode("metrics_metadata")
            .reset_index(drop=True)
            .assign(
                metric_name=lambda df: df.metrics_metadata.apply(getattr, args=["metric"]),
                score=lambda df: df.metrics_metadata.apply(getattr, args=["score"]),
                reason=lambda df: df.metrics_metadata.apply(getattr, args=["reason"]),
            )
            .merge(pd.DataFrame(metric_type), on="metric_name")
            .drop(columns=["success", "metrics_metadata"])
        )

        evaluation.to_csv(f"{self.V_RESULTS}/{self.experiment_name}_val_results.csv", index=False)
        evaluation.head()

    def load_experiment_param_data(
        self,
        experiment_file_name=None,
        benchmark=None,
    ):
        """ """

        if benchmark:
            self.benchmark = benchmark
            self.experiment_file_name = "benchmark"
            benchmark_df = pd.DataFrame()
            benchmark_df["experiment_name"] = ["benchmark"]
            benchmark_df["retrieval_system_prompt"] = [self.ENV.ai.retrieval_system_prompt]
            benchmark_df["retrieval_question_prompt"] = [self.ENV.ai.retrieval_question_prompt]
            self.experiment_parameters = benchmark_df
        else:
            self.experiment_file_name = experiment_file_name
            self.experiment_parameters = pd.read_csv(
                f"notebooks/evaluation/data/experiment_parameters/{self.experiment_file_name}.csv"
            )

    def loop_through_experiements(self):
        """ """
        for index, row in self.experiment_parameters.iterrows():
            self.experiment_name = row["experiment_name"]
            self.retrieval_system_prompt = (row["retrieval_system_prompt"],)
            self.retrieval_question_prompt = row["retrieval_question_prompt"]

            self.write_rag_results()
            self.do_evaluation()
            self.write_evaluation_results()

    def empirical_ci(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate confidence intervals for aggregated metrics."""

        df_grouped = (
            df.groupby(["experiment_name", "metric_name"])["score"]
            .agg(["mean", "sem", "min", "max", "count"])
            .reset_index()
        )

        ci = stats.t.interval(
            confidence=0.95, df=df_grouped["count"] - 1, loc=df_grouped["mean"], scale=df_grouped["sem"]
        )

        df_grouped["ci_low"] = ci[0]
        df_grouped["ci_high"] = ci[1]

        return df_grouped

    def create_visualisation_plus_grouped_results(self):
        """ """
        experiments = []
        experiment_names = self.experiment_parameters["experiment_name"]
        for experiment_name in experiment_names:
            experiment = pd.read_csv(f"{self.V_RESULTS}/{self.experiment_name}_val_results.csv")
            experiment["experiment_name"] = experiment_name
            experiments.append(experiment)

        experiments_df = pd.concat(experiments)

        # Note that the confidence intervals in sns.barplot is calculated by bootstrapping.
        # See empirical_ci() above for empirical confidence interval calculation.
        barplot = sns.barplot(experiments_df, x="score", y="metric_name", hue="experiment_name", errorbar=("ci", 95))
        fig = barplot.get_figure()
        fig.savefig(f"{self.V_RESULTS}/{self.experiment_file_name}_boxplot.png", bbox_inches="tight")

        experiment_metrics = self.empirical_ci(experiments_df)
        experiment_metrics.to_csv(f"{self.V_RESULTS}/{self.experiment_file_name}_eval_results_full.csv")


@click.command()
@click.option(
    "--data_version",
    required=True,
    type=str,
    help="Specify the data version you want to use.",
)
@click.option(
    "--experiment_file_name",
    required=False,
    type=str,
    help="Specify the experiment data file name you want to use. (CSV)",
)
# @click.option(
#     "--overwrite",
#     "-o",
#     required=False,
#     is_flag=True,
#     help="Overwrite existing results"
# )
# @click.option('--exp_data', help="Specify name of experiments to run")
@click.option(
    "--benchmark", "-b", required=False, is_flag=True, help="Use the baseline rag function to get benchmarking results."
)
def main(data_version, experiment_file_name, benchmark):
    get_experiment_results = GetExperimentResults()
    get_experiment_results.set_data_version(data_version)
    get_experiment_results.load_experiment_param_data(experiment_file_name=experiment_file_name, benchmark=benchmark)
    get_experiment_results.load_chunks_from_jsonl_to_index()
    get_experiment_results.loop_through_experiements()
    get_experiment_results.create_visualisation_plus_grouped_results()
    get_experiment_results.clear_index()


if __name__ == "__main__":
    main()
