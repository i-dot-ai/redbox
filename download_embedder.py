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
        required=False,
        help="Name of the Sentence Transformer Model",
        default=None,
    )

    args = parser.parse_args()

    if args.model_name is None:
        logging.error("❓ No model name provided. Attempting to load EMBEDDING_MODEL from environment")
        return
    else:
        logging.info(f"🔎 Model name provided: {args.model_name}")
        model_name = args.model_name

    log.info(f"💾 Downloading Sentence Transformer Embedder: {model_name}")
    SentenceTransformerDB(model_name)
    log.info(f"✅ Downloaded Sentence Transformer Embedder: {model_name}")


if __name__ == "__main__":
    download()
