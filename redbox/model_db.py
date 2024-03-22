import collections
import logging
import os

from sentence_transformers import SentenceTransformer

from redbox.models import ModelInfo, Settings

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models")

log = logging.getLogger()
log.setLevel(logging.INFO)

env = Settings()


class SentenceTransformerDB(collections.UserDict):
    def __init__(self):
        super().__init__()
        self[env.embedding_model] = SentenceTransformer(env.embedding_model, cache_folder=MODEL_PATH)

    def __getitem__(self, model_name: str) -> SentenceTransformer:
        return super().__getitem__(model_name)

    def get_model_info(self, model_name: str) -> ModelInfo:
        model_obj = self[model_name]
        model_info = ModelInfo(
            model=model_name,
            max_seq_length=model_obj.get_max_seq_length(),
            vector_size=model_obj.get_sentence_embedding_dimension(),
        )
        return model_info
