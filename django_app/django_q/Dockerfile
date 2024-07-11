# poetry
FROM python:3.12-slim AS poetry-packages

RUN apt-get update && apt-get install --yes build-essential > /dev/null

RUN pip install poetry poetry-plugin-bundle

WORKDIR /src

COPY django_app/pyproject.toml .
COPY django_app/poetry.lock .

# do this so that poetry bundle can run without the project - can't pass --no-root to bundle
RUN poetry install
RUN poetry bundle venv ./venv


# app
FROM python:3.12-slim

RUN apt-get update && apt-get install --yes libpq-dev curl > /dev/null

WORKDIR /usr/src/app

COPY django_app/ .
COPY --from=poetry-packages /src/venv ./venv

ENV DJANGO_SETTINGS_MODULE='redbox_app.settings'
ENV PYTHONPATH "${PYTHONPATH}:/."

EXPOSE 8091
CMD ["venv/bin/python", "manage.py", "qcluster"] 