FROM python:3.11

RUN apt-get update

RUN pip install poetry

# Optimise image size with poetry by defining cache dir to be deleted after installation
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

ADD ../pyproject.toml ../poetry.lock ./

# Install the dependencies (with necessary dependency groups) and remove the cache dir (to reduce image size)
RUN poetry install --no-root --no-ansi --with worker,api --without ai,streamlit-app,ingest,dev,embed && rm -rf $POETRY_CACHE_DIR

ADD ./redbox /app/redbox
ADD ./Makefile /app/
ADD ./.env.example /app/

WORKDIR /app/
