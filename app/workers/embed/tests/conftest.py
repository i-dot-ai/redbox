import pytest
from fastapi.testclient import TestClient

from ..app import app, model_info


@pytest.fixture
def client():
    yield TestClient(app)


@pytest.fixture
def example_modes():
    model_info["a"] = {"model": "A", "max_seq_length": 1, "vector_size": 2}
    model_info["b"] = {"model": "A", "max_seq_length": 1, "vector_size": 2}
    yield model_info
