FROM python:3.11-buster as builder
ARG EMBEDDING_MODEL


RUN pip install poetry

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /app/
ADD pyproject.toml poetry.lock ./

RUN --mount=type=cache,target=$POETRY_CACHE_DIR poetry install --no-root --no-ansi --with worker,ingest --without ai,dev,api,streamlit-app

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app/
ADD redbox/ /app/redbox
ADD ingest/ /app/ingest
ADD download_embedder.py /app/

# Download the model
RUN python download_embedder.py --model_name ${EMBEDDING_MODEL}

CMD ["faststream", "run", "ingest.src.worker:app"]
