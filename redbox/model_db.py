import logging
import os
from uuid import uuid4

from sentence_transformers import SentenceTransformer

from redbox.models.embedding import Embedding, EmbeddingResponse, EmbeddingModelInfo

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models")

log = logging.getLogger()
log.setLevel(logging.INFO)


class SentenceTransformerDB(SentenceTransformer):
    def __init__(self, embedding_model_name: str):
        super().__init__(embedding_model_name, cache_folder=MODEL_PATH)
        self.embedding_model_name = embedding_model_name

    def embed_sentences(self, sentences: list[str]) -> EmbeddingResponse:
        embeddings = self.encode(sentences)

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
            embedding_model=self.embedding_model_name,
            embedding_model_info=self.get_embedding_model_info(),
        )

        return output

    def get_embedding_model_info(self) -> EmbeddingModelInfo:
        embedding_model_info = EmbeddingModelInfo(
            embedding_model=self.embedding_model_name,
            vector_size=self.get_sentence_embedding_dimension(),
        )
        return embedding_model_info
