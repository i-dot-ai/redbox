FROM python:3.11-buster as builder

WORKDIR /app/

RUN pip install poetry

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

ADD pyproject.toml poetry.lock /app/
ADD redbox-core /app/redbox-core
ADD README.md /app/README.md

COPY notebooks/evaluation/app.py /app/

RUN --mount=type=cache,target=$POETRY_CACHE_DIR poetry install --no-root --no-ansi

FROM python:3.11-slim as runtime

WORKDIR /app/

RUN apt-get update && apt-get install --yes libpq-dev curl > /dev/null

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

COPY --from=builder /app/.venv /app/.venv

COPY notebooks/evaluation /app/notebooks/evaluation

EXPOSE 8501

CMD ["streamlit", "run", "notebooks/evaluation/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
