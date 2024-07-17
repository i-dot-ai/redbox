import json
import sys
from pathlib import Path
from unittest import mock

import pytest

# Hack - wasn't picking up imports properly
sys.path.append(str(Path(__file__).parents[2]))
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
from elasticsearch import Elasticsearch
from elasticsearch.helpers import scan
from evaluation.rag_experiments import GetExperimentResults

from redbox.models import Settings


@pytest.fixture()
def env():
    return Settings()


@pytest.fixture()
def es_client():
    with (
        mock.patch("elasticsearch.Elasticsearch.search") as mocked_search,
        mock.patch("elasticsearch.client.IndicesClient.create") as mocked_index_create,
        mock.patch("elasticsearch.Elasticsearch.index") as mocked_index,
        mock.patch("elasticsearch.helpers.scan") as mocked_scan,
        mock.patch("elasticsearch.Elasticsearch.delete_by_query") as mocked_delete_by_query,
    ):
        mocked_search.return_value = {"hits": {"hits": [{"_id": "1", "_source": {"field": "value"}}]}}
        mocked_index_create.return_value = {"acknowledged": True}
        mocked_index.return_value = {"result": "created"}
        mocked_delete_by_query.return_value = {"deleted": 1}
        mocked_scan.return_value = iter(
            [{"_id": "1", "_source": {"field": "value"}}, {"_id": "2", "_source": {"field": "value"}}]
        )

        client = Elasticsearch(hosts=["http://localhost:9200"])
        client.indices = mock.Mock()
        client.indices.create = mocked_index_create
        client.search = mocked_search
        client.index = mocked_index
        client.delete_by_query = mocked_delete_by_query

        yield client, mocked_search, mocked_index_create, mocked_index, mocked_scan, mocked_delete_by_query


@pytest.mark.usefixtures("es_client")
class TestGetExperimentResults(unittest.TestCase):
    @pytest.fixture(autouse=True)
    def inject_fixtures(self, es_client):
        (
            self.es_client,
            self.mocked_search,
            self.mocked_index_create,
            self.mocked_index,
            self.mocked_scan,
            self.mocked_delete_by_query,
        ) = es_client

        return es_client

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def setUp(self):
        self.get_experiment_results = GetExperimentResults()
        self.get_experiment_results.set_data_version("0.2.3")

        self.get_experiment_results.ENV = MagicMock()

        self.get_experiment_results.ES_CLIENT = self.es_client

        self.temp_dir = tempfile.TemporaryDirectory()
        self.get_experiment_results.V_RESULTS = self.temp_dir.name

        self.mock_synthetic_path = "/mock/synthetic"
        self.mock_complete_ragas_file = "mock_complete_ragas_synthetic_data.csv"
        self.get_experiment_results.synthetic_data_dir = self.mock_synthetic_path

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch("jsonlines.open")
    def test_load_chunks_from_jsonl_to_index(self, mock_jsonlines_open):
        mock_jsonlines_open.return_value.__enter__.return_value = iter(
            [json.dumps({"uuid": "1234", "parent_file_uuid": "abcd", "data": "test data"})]
        )

        file_uuids = self.get_experiment_results.load_chunks_from_jsonl_to_index()
        assert "abcd" in file_uuids
        self.get_experiment_results.ES_CLIENT.index.assert_called_once()

    @patch("jsonlines.open")
    def test_load_chunks_from_empty_jsonl(self, mock_jsonlines_open):
        mock_jsonlines_open.return_value.__enter__.return_value = iter([])

        result = self.get_experiment_results.load_chunks_from_jsonl_to_index()
        assert result == set()

    def test_load_experiment_param_data(self):
        with patch("pandas.read_csv") as mock_read_csv:
            mock_read_csv.return_value = pd.DataFrame(
                {
                    "experiment_name": ["test_experiment"],
                    "retrieval_system_prompt": ["test_prompt"],
                    "retrieval_question_prompt": ["test_question_prompt"],
                }
            )

            self.get_experiment_results.load_experiment_param_data("test_file")
            assert self.get_experiment_results.experiment_parameters["experiment_name"][0] == "test_experiment"

    @patch("evaluation.rag_experiments.GetExperimentResults.get_rag_results")
    @patch("pandas.DataFrame.to_csv")
    def test_write_rag_results(self, mock_to_csv, mock_get_rag_results):
        mock_get_rag_results.return_value = {
            "output_text": "test_output",
            "source_documents": [{"page_content": "test_content"}],
        }

        with patch("pandas.read_csv") as mock_read_csv:
            mock_read_csv.return_value = pd.DataFrame({"input": ["test_input"]})
            self.get_experiment_results.write_rag_results()
            mock_to_csv.assert_called_once()

    @patch("evaluation.rag_experiments.pd.read_csv")
    @patch("evaluation.rag_experiments.evaluate")
    def test_do_evaluation(self, mock_evaluate, mock_read_csv):
        # Setting up the mock return value for read_csv
        mock_data = pd.DataFrame({"column1": [1, 2, 3], "column2": ["a", "b", "c"]})
        mock_read_csv.return_value = mock_data

        mock_eval_result = pd.DataFrame(
            {
                "input": ["input1", "input2", "input3"],
                "actual_output": ["output1", "output2", "output3"],
                "expected_output": ["expected1", "expected2", "expected3"],
                "context": [["context1"], ["context2"], ["context3"]],
                "retrieval_context": [["retrieval1"], ["retrieval2"], ["retrieval3"]],
                "additional_metadata": [None, None, None],
                "comments": [None, None, None],
            }
        )
        mock_evaluate.return_value = mock_eval_result

        result = self.get_experiment_results.do_evaluation()

        assert result is not None
        assert isinstance(result, pd.DataFrame)
        assert result.shape == (3, 7)

    @patch("seaborn.barplot")
    @patch("pandas.concat")
    @patch("pandas.read_csv")
    def test_create_visualisation_plus_grouped_results(self, mock_read_csv, mock_concat, mock_barplot):  # noqa: ARG002
        mock_read_csv.return_value = pd.DataFrame(
            {"experiment_name": ["test_experiment"], "score": [0.5], "metric_name": ["test_metric"]}
        )
        mock_concat.return_value = mock_read_csv.return_value

        self.get_experiment_results.experiment_parameters = {"experiment_name": ["test_experiment"]}
        self.get_experiment_results.create_visualisation_plus_grouped_results()

    @patch("pandas.read_csv")
    def test_create_visualisation_empty_data(self, mock_read_csv):
        mock_read_csv.return_value = pd.DataFrame()
        self.get_experiment_results.experiment_parameters = {"experiment_name": []}

        with pytest.raises(ValueError):  # noqa: PT011
            self.get_experiment_results.create_visualisation_plus_grouped_results()

    @patch("jsonlines.open")
    def test_clear_index(self, mock_jsonlines_open):
        with patch("pandas.read_csv") as mock_read_csv:
            mock_read_csv.return_value = pd.DataFrame(
                {
                    "experiment_name": ["test_experiment"],
                    "retrieval_system_prompt": ["test_prompt"],
                    "retrieval_question_prompt": ["test_question_prompt"],
                }
            )

            self.get_experiment_results.load_experiment_param_data("test_file")

            mock_jsonlines_open.return_value.__enter__.return_value = iter(
                [json.dumps({"uuid": "1234", "parent_file_uuid": "abcd", "data": "test data"})]
            )

            self.get_experiment_results.load_chunks_from_jsonl_to_index()

            self.get_experiment_results.ES_CLIENT.index.assert_called_once()

            self.get_experiment_results.clear_index()
            documents_after_clear = list(
                scan(self.get_experiment_results.ES_CLIENT, query={"query": {"match_all": {}}})
            )
            assert len(documents_after_clear) == 0

            self.get_experiment_results.clear_index()


if __name__ == "__main__":
    unittest.main()
