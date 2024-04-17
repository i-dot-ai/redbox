FROM python:3.11-buster as builder

RUN pip install poetry

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /app/
ADD pyproject.toml poetry.lock ./
ADD download_embedder.py /app/

RUN --mount=type=cache,target=$POETRY_CACHE_DIR poetry install --no-root --no-ansi --with worker,api --without ai,ingester,dev


FROM python:3.11-slim-buster as runtime
ARG EMBEDDING_MODEL

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

WORKDIR /app/

# Add the rest of the files
ADD redbox/ /app/redbox
ADD embedder/ /app/embedder
ADD download_embedder.py /app/

EXPOSE 5000

# Download the model
RUN python download_embedder.py --model_name ${EMBEDDING_MODEL}

CMD ["uvicorn", "embedder.src.worker:app", "--host", "0.0.0.0", "--port", "5000"]
