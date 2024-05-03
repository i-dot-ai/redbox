FROM python:3.11-buster as builder

RUN pip install poetry

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /app/
ADD pyproject.toml poetry.lock ./

RUN --mount=type=cache,target=$POETRY_CACHE_DIR poetry install --no-root --no-ansi --with worker,api --without ai,dev

FROM python:3.11-slim-buster as runtime
RUN apt update && apt-get install -y \
    poppler-utils \
    tesseract-ocr \
    libmagic-dev

ARG EMBEDDING_MODEL

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

WORKDIR /app/
ADD redbox/ /app/redbox
ADD worker/ /app/worker

# Download the Embedding and OCR models
RUN python worker/download_models.py --embedding_model ${EMBEDDING_MODEL}

# Downlaod Sentence Tokenizer
RUN python -m nltk.downloader punkt

# Download POS tagger
RUN python -m nltk.downloader averaged_perceptron_tagger

CMD ["uvicorn", "worker.src.app:app", "--host", "0.0.0.0", "--port", "5000"]
