FROM python:3.11-buster as builder

WORKDIR /mlflow

RUN pip install poetry

ADD ../pyproject.toml ../poetry.lock ./
RUN --mount=type=cache,target=/root/.cache poetry install --no-root --no-ansi --with mlflow

EXPOSE 5010

CMD mlflow deployments start-server --config-path config.yaml