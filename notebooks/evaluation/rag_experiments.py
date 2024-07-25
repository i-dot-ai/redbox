import json
import sys
from dataclasses import asdict
from operator import itemgetter
from pathlib import Path
from typing import Annotated

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

# Temp hack - there is an issue with the importing of redbox-core
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
    """
    Class to handle experiment results retrieval and processing.

    Attributes:
        data_version (str): Data version to be used in experiment
        benchmark (bool): Benchmark stated or not
        V_EMBEDDINGS (str): Embeddings version
        V_ROOT (path): Path to where the root of experiment data lies
        V_SYNTHETIC (path): Path to the synthetic data
        V_RESULTS (path): Path to the results from data processing
        MODEL (str): Embedding model
        ES_CLIENT (func): Elastic search client from settings
        INDEX (str): Index for the json lines file
        experiment_name (str): Name of the experiment
    """

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
        """
        This function sets the necessary environment variables depending on your data version.
        It assumes you have a versioned evaluation folder in your repository e.g. notebooks/evaluation/data/0.2.0
        This should be copied from the Redbox shared Google Drive.
        This folder contains the raw files, QA sets, embeddings etc.
        """
        self.data_version = data_version
        root = Path(__file__).parents[2]
        evaluation_dir = root / "notebooks/evaluation"
        self.V_ROOT = evaluation_dir / f"data/{self.data_version}"
        self.V_SYNTHETIC = self.V_ROOT / "synthetic"
        self.V_RESULTS = self.V_ROOT / "results"
        self.V_EMBEDDINGS = self.V_ROOT / "embeddings"
        self.MODEL = self.ENV.embedding_model
        self.INDEX = f"{self.data_version}-{self.MODEL}".lower()
        self.ES_CLIENT = self.ENV.elasticsearch_client()

    def load_chunks_from_jsonl_to_index(self) -> set:
        """
        This function takes the versioned embeddings (e.g. from notebooks/evaluation/data/0.2.0/embeddings)
        and loads them to ElasticSearch.
        """
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
        """
        This function clears the indexes from ElasticSearch.
        """
        if not self.ES_CLIENT.indices.exists(index=self.INDEX):
            return None

        documents = list(scan(self.ES_CLIENT, index=self.INDEX, query={"query": {"match_all": {}}}))
        bulk_data = [{"_op_type": "delete", "_index": doc["_index"], "_id": doc["_id"]} for doc in documents]
        if bulk_data:
            return bulk(self.ES_CLIENT, bulk_data, request_timeout=300)
        return None

    def get_parameterised_retriever(
        self, es: Annotated[Elasticsearch, Depends(dependencies.get_elasticsearch_client)]
    ) -> BaseRetriever:
        """
        Creates an Elasticsearch retriever runnable.
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
        llm: Annotated[ChatLiteLLM, Depends(dependencies.get_llm)],
        retriever: Annotated[VectorStoreRetriever, Depends(dependencies.get_parameterised_retriever)],
        tokeniser: Annotated[Encoding, Depends(dependencies.get_tokeniser)],
        env: Annotated[Settings, Depends(dependencies.get_env)],
    ) -> Runnable:
        """
        This is an adaptation of core_api.src.build_chains.build_retrieval_chain.
        Function experiements with different retrieval_system_prompt and retrieval_question_prompt.
        """
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
        """
        Get Redbox response for a given question.
        """
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
            dict_chunk = dict(chunk)
            filtered_chunk = {
                "page_content": dict_chunk["page_content"],
                "page_number": dict_chunk["metadata"]["page_number"],
                "parent_file_uuid": dict_chunk["metadata"]["parent_file_uuid"],
            }
            filtered_chunks.append(filtered_chunk)

        return {"output_text": response["response"], "source_documents": filtered_chunks}

    def write_rag_results(self) -> None:
        """
        Format and write Redbox responses to evaluation dataset.
        """

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

        return self.eval_results

    def write_evaluation_results(self) -> None:
        """
        This function writes the evaluation results to a csv, identifiable by experiment_name.
        """
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
        """
        This function loads an csv of experiments to try unless benchmark is specified;
        in this case it will take the core_api retrieval_system_prompt and retrieval_question_prompt.
        """

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
        """
        This function calls the other functions to run and write the different experiments.
        """
        for _index, row in self.experiment_parameters.iterrows():
            self.experiment_name = row["experiment_name"]
            self.retrieval_system_prompt = (row["retrieval_system_prompt"],)
            self.retrieval_question_prompt = row["retrieval_question_prompt"]

            self.write_rag_results()
            self.do_evaluation()
            self.write_evaluation_results()

    def empirical_ci(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate confidence intervals for aggregated metrics.
        """

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
        """
        This function uses the stored experiment result to save the aggregated metics using empirical_ci().
        It also saves a barplot (here confidence intervals are calculated by bootstrapping).
        """
        experiments = []
        experiment_names = self.experiment_parameters["experiment_name"]
        for experiment_name in experiment_names:
            experiment = pd.read_csv(f"{self.V_RESULTS}/{self.experiment_name}_val_results.csv")
            experiment["experiment_name"] = experiment_name
            experiments.append(experiment)

        experiments_df = pd.concat(experiments)

        barplot = sns.barplot(experiments_df, x="score", y="metric_name", hue="experiment_name", errorbar=("ci", 95))
        fig = barplot.get_figure()
        fig.savefig(f"{self.V_RESULTS}/{self.experiment_file_name}_boxplot.png", bbox_inches="tight")

        experiment_metrics = self.empirical_ci(experiments_df)
        experiment_metrics.to_csv(f"{self.V_RESULTS}/{self.experiment_file_name}_eval_results_full.csv")


class Mutex(click.Option):
    def __init__(self, *args, **kwargs):
        self.not_required_if = kwargs.pop("not_required_if")
        self.required_if_not_set = kwargs.pop("required_if_not_set", True)

        if not self.not_required_if:
            msg = "'not_required_if' parameter required"
            raise ValueError(msg)

        kwargs["help"] = (
            kwargs.get("help", "") + " Option is mutually exclusive with " + ", ".join(self.not_required_if) + "."
        ).strip()
        super().__init__(*args, **kwargs)

    def handle_parse_result(self, ctx, opts, args):
        current_opt = self.name in opts
        for mutex_opt in self.not_required_if:
            if mutex_opt in opts:
                if current_opt:
                    msg = f"Illegal usage: '{self.name}' is mutually exclusive with {mutex_opt}."
                    raise click.UsageError(msg)
                self.prompt = None

        if not current_opt and self.required_if_not_set and not any(opt in opts for opt in self.not_required_if):
            msg = f"Illegal usage: Either '{self.name}' or one of {', '.join(self.not_required_if)} must be provided."
            raise click.UsageError(msg)
        return super().handle_parse_result(ctx, opts, args)


@click.command()
@click.option(
    "--data_version",
    required=True,
    type=str,
    help="Specify the data version you want to use.",
)
@click.option(
    "--experiment_file_name",
    cls=Mutex,
    not_required_if=["benchmark"],
    required_if_not_set=True,
    type=str,
    help="Specify the experiment data file name you want to use. (CSV)",
)
@click.option(
    "--benchmark",
    "-b",
    cls=Mutex,
    not_required_if=["experiment_file_name"],
    required_if_not_set=True,
    is_flag=True,
    help="Use the baseline rag function to get benchmarking results.",
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
