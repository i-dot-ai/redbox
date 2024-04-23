FROM python:3.11-buster as builder

WORKDIR /app/

RUN pip install poetry
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Add redbox python package and install it with poetry
ADD redbox/ /app/redbox
ADD pyproject.toml poetry.lock /app/
ADD redbox/ /app/redbox

RUN --mount=type=cache,target=$POETRY_CACHE_DIR poetry install --no-root --no-ansi --with api,ai --without ingester,dev,worker

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
ARG EMBEDDING_MODEL_PATH

WORKDIR /app/

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}
COPY --from=embeddings ${EMBEDDING_MODEL_PATH} ${EMBEDDING_MODEL_PATH}

COPY core_api/ /app/core_api/
ADD redbox/ /app/redbox

ENV PYTHONPATH "/app"

# Run FastAPI
EXPOSE 5002
CMD ["uvicorn", "core_api.src.app:app", "--host", "0.0.0.0", "--port", "5002"]