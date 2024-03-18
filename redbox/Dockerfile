FROM python:3.11

RUN apt-get update

RUN pip install poetry

ADD ../pyproject.toml ../poetry.lock ./
RUN poetry install --no-root --no-ansi --with worker,api --without ai,streamlit-app,ingest,dev,embed

ADD ./redbox /app/redbox
ADD ./Makefile /app/
ADD ./.env.example /app/

WORKDIR /app/
