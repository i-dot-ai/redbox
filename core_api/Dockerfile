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
ADD download_embedder.py /app/
ADD redbox/ /app/redbox

RUN --mount=type=cache,target=$POETRY_CACHE_DIR poetry install --no-root --no-ansi --with api --without ai,ingester,dev,worker,streamlit-app

FROM python:3.11-slim-buster as runtime
ARG EMBEDDING_MODEL

WORKDIR /app/

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"
COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

ADD core_api/src/app.py /app/app.py
ADD download_embedder.py /app/
ADD redbox/ /app/redbox

# Download the model
RUN type=cache python download_embedder.py --model_name ${EMBEDDING_MODEL}

# Run FastAPI
EXPOSE 5002
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5002"]