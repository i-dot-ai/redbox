FROM python:3.12-bookworm as builder

RUN apt update && apt-get install -y \
    poppler-utils \
    tesseract-ocr \
    libmagic-dev

RUN pip install poetry

ADD redbox-core/ /app/redbox-core
ADD worker/ /app/worker
ADD README.md /app/README.md

WORKDIR /app/worker

RUN poetry install --without dev

# Downlaod Sentence Tokenizer
RUN poetry run python -m nltk.downloader punkt

# Download POS tagger
RUN poetry run python -m nltk.downloader averaged_perceptron_tagger

# Download the OCR models
RUN poetry run python -m download_ocr_models

RUN chmod +x health.sh

CMD ["poetry", "run", "faststream", "run", "worker.app:app"]
