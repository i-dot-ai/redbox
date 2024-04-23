import logging
import os
from uuid import uuid4
from typing import List
from sentence_transformers import SentenceTransformer

from redbox.models import EmbeddingModelInfo
from redbox.models.embedding import Embedding, EmbeddingResponse

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models")

log = logging.getLogger()
log.setLevel(logging.INFO)


class SentenceTransformerDB(SentenceTransformer):
    def __init__(self, model_name: str):
        super().__init__(model_name, cache_folder=MODEL_PATH)
        self.model_name = model_name

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
            model=self.model_name,
            embedding_model_info=self.get_embedding_model_info(),
        )

        return output

    def get_embedding_model_info(self) -> EmbeddingModelInfo:
        embedding_model_info = EmbeddingModelInfo(
            model=self.model_name,
            max_seq_length=self.get_max_seq_length(),
            vector_size=self.get_sentence_embedding_dimension(),
        )
        return embedding_model_info

    def embed_query(self, text: str) -> List[float]:
        """Embeds a single sentence. This method is for parity with langchain's Embeddings class.
        https://github.com/langchain-ai/langchain/blob/master/libs/core/langchain_core/embeddings/embeddings.py#L8

        Args:
            text (str): The sentence to embed

        Returns:
            List[float]: The embedding of the sentence
        """
        embedding = self.encode([text])[0].tolist()

        return embedding
