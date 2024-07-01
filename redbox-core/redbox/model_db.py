import logging
from pathlib import Path
from uuid import uuid4

from sentence_transformers import SentenceTransformer  # type: ignore

from redbox.models.embedding import Embedding, EmbeddingModelInfo, EmbeddingResponse

MODEL_PATH = str(Path(__file__).parents[1] / "models")

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

        return EmbeddingResponse(
            object="list",
            data=reformatted_embeddings,
            embedding_id=str(uuid4()),
            embedding_model=self.embedding_model_name,
            embedding_model_info=self.get_embedding_model_info(),
        )

    def get_embedding_model_info(self) -> EmbeddingModelInfo:
        return EmbeddingModelInfo(
            embedding_model=self.embedding_model_name,
            vector_size=self.get_sentence_embedding_dimension(),
        )
