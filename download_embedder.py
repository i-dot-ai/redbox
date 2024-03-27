import argparse
import logging

from redbox.model_db import SentenceTransformerDB

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


def download():
    parser = argparse.ArgumentParser(description="Download Sentence Transformer Embedder")
    parser.add_argument(
        "--model_name",
        type=str,
        required=True,
        help="Name of the Sentence Transformer Model",
    )

    args = parser.parse_args()

    log.info(f"💾 Downloading Sentence Transformer Embedder: {args.model_name}")
    SentenceTransformerDB(args.model_name)
    log.info(f"✅ Downloaded Sentence Transformer Embedder: {args.model_name}")


if __name__ == "__main__":
    download()
