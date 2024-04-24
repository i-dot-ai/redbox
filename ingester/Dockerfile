FROM python:3.11-buster as builder

RUN pip install poetry

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /app/
ADD pyproject.toml poetry.lock ./

RUN --mount=type=cache,target=$POETRY_CACHE_DIR poetry install --no-root --no-ansi --with ingester,api --without ai,dev

FROM python:3.11-buster as embeddings
ARG EMBEDDING_MODEL
ARG EMBEDDING_MODEL_PATH

WORKDIR /app/

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

RUN python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('${EMBEDDING_MODEL}', cache_folder='${EMBEDDING_MODEL_PATH}');"

FROM python:3.11-slim-buster as runtime
RUN apt update && apt-get install -y \
    poppler-utils \
    tesseract-ocr \
    libmagic-dev

ARG EMBEDDING_MODEL

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}
COPY --from=embeddings ${EMBEDDING_MODEL_PATH} ${EMBEDDING_MODEL_PATH}

WORKDIR /app/
ADD redbox/ /app/redbox
ADD ingester/ /app/ingester
ADD ingester/download_ocr_models.py /app/

# Downlaod Sentence Tokenizer
RUN python -m nltk.downloader punkt

# Download POS tagger
RUN python -m nltk.downloader averaged_perceptron_tagger

# Download the OCR models
RUN python download_ocr_models.py

CMD ["uvicorn", "ingester.src.worker:app", "--host", "0.0.0.0", "--port", "5000"]
