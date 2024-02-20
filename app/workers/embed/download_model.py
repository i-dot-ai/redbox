import os

from sentence_transformers import SentenceTransformer

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-mpnet-base-v2")

models_to_download = EMBEDDING_MODEL.split("|")

models_path = "models/"

for model in models_to_download:
    model = SentenceTransformer(model, cache_folder=models_path)
