import collections
import logging
import os
from uuid import uuid4

from sentence_transformers import SentenceTransformer

from redbox.models import ModelInfo, EmbeddingResponse, Settings
from redbox.models.llm import Embedding

env = Settings()
log = logging.getLogger()
log.setLevel(logging.INFO)

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")


class SentenceTransformerDB(collections.UserDict):
    def __init__(self):
        super().__init__()
        """loads the EMBEDDING_MODEL either from the web, or if it exists, the cache"""
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

    def embed_sentences(self, model: str, sentences: list[str]):
        model_obj = self[model]
        embeddings = model_obj.encode(sentences)

        reformatted_embeddings = [
            Embedding(
                object="embedding",
                index=i,
                embedding=list(embedding),
            )
            for i, embedding in enumerate(embeddings)
        ]

        output = EmbeddingResponse(
            object="list",
            data=reformatted_embeddings,
            embedding_id=str(uuid4()),
            model=model,
            model_info=self.get_model_info(model),
        )

        return output


def download():
    SentenceTransformerDB()
