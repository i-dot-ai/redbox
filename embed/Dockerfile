FROM python:3.11-buster as builder

RUN pip install poetry

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /app/
ADD pyproject.toml poetry.lock ./
ADD download_embedder.py /app/

RUN --mount=type=cache,target=$POETRY_CACHE_DIR poetry install --no-root --no-ansi --with worker,api --without ai,ingest,dev,streamlit-app


FROM python:3.11-slim-buster as runtime

RUN pip install poetry

COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app/
ADD pyproject.toml poetry.lock ./

RUN poetry install --no-root --no-ansi --with worker,api --without ai,ingest,dev,streamlit-app

# Add the rest of the files
ADD redbox/ /app/redbox
ADD ./embed/src/app.py /app/app.py
ADD download_embedder.py /app/
ADD model_db.py /app/

# Download the model
RUN python download_embedder.py

EXPOSE 5000

CMD ["python", "app.py"]
