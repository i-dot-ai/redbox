FROM python:3.11

RUN apt-get update

RUN pip install poetry

ADD ../pyproject.toml ../poetry.lock ./
RUN poetry install --no-root --no-ansi --with dev,worker,api,embed --without ai,streamlit-app,ingest

ADD redbox/ /app/redbox
ADD app/ /app/app
ADD tests /app/tests
ADD Makefile /app/
ADD ../.env.example /app/

WORKDIR /app/
