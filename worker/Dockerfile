FROM python:3.11-buster as builder

RUN pip install poetry

RUN apt update && apt-get install -y \
    poppler-utils \
    tesseract-ocr \
    libmagic-dev

ARG EMBEDDING_MODEL


ADD redbox-core/ /app/redbox-core
ADD worker/ /app/worker
ADD README.md /app/README.md


WORKDIR /app/worker

RUN chmod +x health.sh

# Download the model
# RUN poetry run python worker/download_embedder.py --embedding_model ${EMBEDDING_MODEL}

# RUN poetry add nltk
# # Download Sentence Tokenizer
RUN poetry run python -m nltk.downloader punkt
#
# # Download POS tagger
# RUN python -m nltk.downloader averaged_perceptron_tagger

# Download the OCR models
# RUN python download_ocr_models.py

# CMD ["poetry", "run", "faststream", "run", "worker.app:app", "--workers", "3"]
