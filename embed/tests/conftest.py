import pytest
from sentence_transformers import SentenceTransformer

from fastapi.testclient import TestClient
from embed.src.app import app as application, model_db


def file_pdf_path() -> str:
    return "tests/data/pdf/Cabinet Office - Wikipedia.pdf"


@pytest.fixture
def client():
    yield TestClient(application)


@pytest.fixture
def example_model_db():
    model_db["paraphrase-albert-small-v2"] = SentenceTransformer(
        model_name_or_path="paraphrase-albert-small-v2",
        cache_folder="./models",
    )
    yield model_db
