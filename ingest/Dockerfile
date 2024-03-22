FROM python:3.11-buster as builder

RUN pip install poetry

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /app/
ADD pyproject.toml poetry.lock ./
ADD download_embedder.py /app/

RUN --mount=type=cache,target=$POETRY_CACHE_DIR poetry install --no-root --no-ansi --with worker,ingest --without ai,dev,api,streamlit-app

FROM python:3.11-slim-buster as runtime

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

WORKDIR /app/
ADD redbox/ /app/redbox
ADD ingest/src/app.py /app/app.py
ADD download_embedder.py /app/

# Download the model
RUN python download_embedder.py

# Run pika worker
CMD ["python", "app.py"]
