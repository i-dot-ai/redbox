FROM python:3.11-buster as builder

RUN pip install poetry

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /app/
ADD pyproject.toml poetry.lock ./
# Streamlit app needs a lot of dependencies

RUN --mount=type=cache,target=$POETRY_CACHE_DIR  poetry install --no-root --no-ansi --with streamlit-app,ai,ingester --without dev,worker,api  --no-root

FROM python:3.11-slim-buster as runtime
ARG EMBEDDING_MODEL

RUN apt-get update
RUN apt-get install -y libgl-dev libmagic-dev inetutils-ping

WORKDIR /app/

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

ADD redbox/ /app/redbox
ADD download_embedder.py /app/
RUN python download_embedder.py --model_name ${EMBEDDING_MODEL}
ADD streamlit_app/ /app/streamlit_app
RUN touch /app/__init__.py

ENV PYTHONPATH "/app"

EXPOSE 8501

ENTRYPOINT ["streamlit", "run", "--server.address", "0.0.0.0", "--server.port", "8501", "streamlit_app/Welcome.py" ]
