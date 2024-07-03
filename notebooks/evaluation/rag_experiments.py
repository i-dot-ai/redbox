# TODO: How to integrate with make_evalbackend functionality

from uuid import UUID
import json
import pandas as pd
import pickle
from dataclasses import asdict
from pathlib import Path
import jsonlines
from elasticsearch import Elasticsearch
import click

from redbox.models import Settings
from redbox.models.settings import ElasticLocalSettings
from redbox.models import Settings

from langchain.globals import set_verbose

from elasticsearch import Elasticsearch
from langchain_community.chat_models import ChatLiteLLM
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import ConfigurableField

from redbox.models import Settings
from redbox.models.file import UUID

set_verbose(False)

from dotenv import find_dotenv, load_dotenv

_ = load_dotenv(find_dotenv())

@click.command()
@click.option('--data_version', help="Specify the data version you want to use.")
def get_data_version(data_version):
    return data_version


ENV = Settings(minio_host="localhost", elastic=ElasticLocalSettings(host="localhost"))

DATA_VERSION = get_data_version()
ROOT = Path(__file__).parents[2]
EVALUATION_DIR = ROOT / "notebooks/evaluation"

V_ROOT = EVALUATION_DIR / f"data/{DATA_VERSION}"
V_RAW = V_ROOT / "raw"
V_SYNTHETIC = V_ROOT / "synthetic"
V_CHUNKS = V_ROOT / "chunks"
V_RESULTS = V_ROOT / "results"
V_EMBEDDINGS = V_ROOT / "embeddings"

V_ROOT.mkdir(parents=True, exist_ok=True)
V_RAW.mkdir(parents=True, exist_ok=True)
V_SYNTHETIC.mkdir(parents=True, exist_ok=True)
V_CHUNKS.mkdir(parents=True, exist_ok=True)
V_RESULTS.mkdir(parents=True, exist_ok=True)
V_EMBEDDINGS.mkdir(parents=True, exist_ok=True)

MODEL = ENV.embedding_model
INDEX = f"{DATA_VERSION}-{MODEL}".lower()
# USER_UUID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
# S3_CLIENT = ENV.s3_client()
ES_CLIENT = ENV.elasticsearch_client()


# @click.option('--exp_data', help="Specify name of experiments to run")

def load_chunks_from_jsonl_to_index(data_version: str) -> set:
    
 
    file_uuids = set()
    file_path=V_EMBEDDINGS / f"{MODEL}.jsonl"
    
    with jsonlines.open(file_path, mode="r") as reader:
        for chunk_raw in reader:
            chunk = json.loads(chunk_raw)
            ES_CLIENT.index(
                index=INDEX,
                id=chunk["uuid"],
                body=chunk,
            )

            file_uuids.add(chunk["parent_file_uuid"])

    return file_uuids

if __name__ == '__main__':
    get_data_version()
    load_chunks_from_jsonl_to_index()

FILE_UUIDS = load_chunks_from_jsonl_to_index()



# TODO: Integrate with experiment prompts csv
# TODO: Import and use chain functions as existing in the repository
# TODO: Generate metric results and store somwhere?
# TODO: Delete data from elastic once done.???
