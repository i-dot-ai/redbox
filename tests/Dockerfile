FROM python:3.11

RUN apt-get update

RUN pip install poetry

ADD ../pyproject.toml ../poetry.lock ./
RUN poetry install --no-root --no-ansi --with dev,worker,api,ingest,embed --without ai,streamlit-app

ADD redbox/ /app/redbox
ADD tests /app/tests
ADD ../.env.test /app/

WORKDIR /app/
