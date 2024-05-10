# npm
# use the same base image as the others for efficiency
FROM python:3.11-slim AS npm-packages

RUN apt-get update && apt-get install --yes nodejs npm > /dev/null

WORKDIR /src

COPY django_app/frontend/package.json .
RUN npm install


# poetry
FROM python:3.11-slim AS poetry-packages

RUN apt-get update && apt-get install --yes build-essential > /dev/null

RUN pip install poetry poetry-plugin-bundle

WORKDIR /src

COPY django_app/pyproject.toml .
COPY django_app/poetry.lock .

# do this so that poetry bundle can run without the project - can't pass --no-root to bundle
#RUN touch README.md
RUN poetry install
RUN poetry bundle venv ./venv


# app
FROM python:3.11-slim

RUN apt-get update && apt-get install --yes libpq-dev > /dev/null

WORKDIR /usr/src/app

COPY --from=npm-packages /src/node_modules /app/frontend/node_modules
COPY --from=poetry-packages /src/venv ./venv

COPY django_app/ .

ENV DJANGO_SETTINGS_MODULE='redbox_app.settings.py'
ENV PYTHONPATH "${PYTHONPATH}:/."

EXPOSE 8090

RUN chmod +x start.sh
CMD ["./start.sh"]