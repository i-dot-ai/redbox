import collections
import logging
import os
from uuid import uuid4

from sentence_transformers import SentenceTransformer

from redbox.models import EmbeddingResponse, ModelInfo
from redbox.models.llm import Embedding

log = logging.getLogger()
log.setLevel(logging.INFO)


class SentenceTransformerDB(collections.UserDict):
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

    def init_from_disk(self, filepath: str = "models"):
        available_models = []

        for dirpath, dirnames, filenames in os.walk(filepath):
            # Check if the current directory contains a file named "config.json"
            if "pytorch_model.bin" in filenames:
                # If it does, print the path to the directory
                available_models.append(dirpath)

        for model_path in available_models:
            model_name = model_path.split("/")[-3]
            model = model_name.split("--")[-1]
            self[model] = SentenceTransformer(model_path)
            log.info(f"Loaded model {model}")

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
