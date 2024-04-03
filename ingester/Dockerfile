FROM python:3.11-buster as builder

RUN pip install poetry

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /app/
ADD pyproject.toml poetry.lock ./
ADD download_embedder.py /app/

RUN --mount=type=cache,target=$POETRY_CACHE_DIR poetry install --no-root --no-ansi --with worker,ingester --without ai,dev,api,streamlit-app

FROM python:3.11-slim-buster as runtime
RUN apt update && sudo apt-get install -y \
    poppler-utils \
    tesseract-ocr

ARG EMBEDDING_MODEL

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

WORKDIR /app/
ADD redbox/ /app/redbox
ADD ingester/ /app/ingester
ADD download_embedder.py /app/

# Download the model
RUN python download_embedder.py --model_name ${EMBEDDING_MODEL}

CMD ["faststream", "run", "ingester.src.worker:app"]