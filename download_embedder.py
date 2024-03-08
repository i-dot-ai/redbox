import argparse
import logging
import os

from sentence_transformers import SentenceTransformer

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

    parser.add_argument(
        "--models_path",
        type=str,
        required=False,
        help="Path to store the downloaded models",
        default="models",
    )

    args = parser.parse_args()

    model_name = "all-mpnet-base-v2"

    if args.model_name is None:
        logging.warning("❓ No model name provided. Attempting to load EMBEDDING_MODEL from environment")
        try:
            model_name = os.environ["EMBEDDING_MODEL"]
        except KeyError:
            logging.warning(
                "❓ No model name provided and EMBEDDING_MODEL not found in environment. Defaulting to all-mpnet-base-v2"
            )
    else:
        logging.info(f"🔎 Model name provided: {args.model_name}")
        model_name = args.model_name

    log.info(f"💾 Downloading Sentence Transformer Embedder: {model_name}")
    SentenceTransformer(model_name, cache_folder=args.models_path)
    log.info(f"✅ Downloaded Sentence Transformer Embedder: {model_name} to {args.models_path}")


if __name__ == "__main__":
    download()
