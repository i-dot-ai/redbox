import collections
import logging
import os
from uuid import uuid4

from sentence_transformers import SentenceTransformer

from redbox.models import ModelInfo
from redbox.models.llm import Embedding, EmbeddingResponse

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models")

log = logging.getLogger()
log.setLevel(logging.INFO)


class SentenceTransformerDB(collections.UserDict):
    def __init__(self, model_name):
        super().__init__()
        log.info(f"💾 Downloading Sentence Transformer Embedder: {model_name}")
        self[model_name] = SentenceTransformer(model_name, cache_folder=MODEL_PATH)
        log.info(f"✅ Downloaded Sentence Transformer Embedder: {model_name} to {MODEL_PATH}")

    def __getitem__(self, model_name: str) -> SentenceTransformer:
        return super().__getitem__(model_name)

    def embed_sentences(self, model: str, sentences: list[str]) -> EmbeddingResponse:
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

    def get_model_info(self, model_name: str) -> ModelInfo:
        model_obj = self[model_name]
        model_info = ModelInfo(
            model=model_name,
            max_seq_length=model_obj.get_max_seq_length(),
            vector_size=model_obj.get_sentence_embedding_dimension(),
        )
        return model_info
