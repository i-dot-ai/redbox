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
COPY ../../django_app /app/django_app
COPY django_app/pyproject.toml django_app/poetry.lock /app/django_app/

RUN --mount=type=cache,target=$POETRY_CACHE_DIR poetry install --no-root --no-ansi

WORKDIR /app/django_app
RUN --mount=type=cache,target=$POETRY_CACHE_DIR poetry install --no-root --no-ansi

WORKDIR /app

COPY notebooks/evaluation/app.py /app/

FROM python:3.11-slim as runtime

WORKDIR /app/

RUN apt-get update && apt-get install --yes libpq-dev curl > /dev/null

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/django_app"

COPY --from=builder /app/.venv /app/.venv

COPY notebooks/evaluation /app/notebooks/evaluation
COPY --from=builder /app/django_app /app/django_app

EXPOSE 8501

CMD ["streamlit", "run", "notebooks/evaluation/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
