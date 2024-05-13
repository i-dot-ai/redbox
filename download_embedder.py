import argparse
import logging

from redbox.model_db import SentenceTransformerDB

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


def download():
    parser = argparse.ArgumentParser(description="Download Sentence Transformer Embedder")
    parser.add_argument(
        "--embedding_model",
        type=str,
        required=True,
        help="Name of the Sentence Transformer Model",
    )

    args = parser.parse_args()

    log.info("💾 Downloading Sentence Transformer Embedder: %s", args.embedding_model)
    SentenceTransformerDB(args.embedding_model)
    log.info("✅ Downloaded Sentence Transformer Embedder: %s", args.embedding_model)


if __name__ == "__main__":
    download()
