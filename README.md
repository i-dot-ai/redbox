# 📮 Redbox Copilot

Redbox Copilot is a retrieval augmented generation (RAG) app that uses Claude 2 to organise, categorise and summarise civil service documents. It's designed to handle a variety of administrative sources, such as letters, briefings, minutes, and speech transcripts.

- **Better retrieval**. Redbox Copilot increases organisational memory by indexing documents
- **Faster, accurate summarisation**. Redbox Copilot can summarise reports read months ago, supplement them with current work, and produce a first draft that lets civil servants focus on what they do best

# Local Dev Setup

The entire architecture runs in docker compose for local development. This includes locally hosting the app, databases, object store and orchestration. Therefore, you will need docker installed.

## First time setup

You will need to create a copy of the `.env.example` file as `.env` to store your secrets, such as your Anthropic API key (ask the team for the keys). The `.env` file should not be committed to GitHub.

If you have issues with permissions, you may need to run `chmod 777 data/elastic/` to be able to write to the folder.

## To run

You can simply run:

`docker compose up` or `make run`

You'll find a series of useful `docker compose` commands already maded in [`Makefile`](./Makefile)

Any time you update code for the the repo, you'll likely need to rebuild the containers.

# Codespace

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/i-dot-ai/redbox-copilot?quickstart=1)

# Development

- Download and install [pre-commit](https://pre-commit.com) to benefit from pre-commit hooks
  - `pip install pre-commit`
  - `pre-commit install`

# Dependencies

This project uses a microservice architecture.

Each microservice runs in its own container defined by a `Dockerfile`.

For every microservice that we have written in python we define its dependencies using https://python-poetry.org/.

This means that our project is structured approximately like this:

```txt
redbox-copilot/
├── app/
│  ├── frontend/
│  └── workers/
│     ├── embed
│     │  ├── Dockerfile
│     │  └── pyproject.toml
│     └── ingest
│        ├── Dockerfile
│        └── pyproject.toml
├── legacy_app/
│  └── Dockerfile
├── redbox/
├── docker-compose.yaml
├── pyproject.toml
└── README.md
```

Where the top level `pyproject.toml` is currently closely associated with `lagacy_app` and `redbox`.

## Troubleshooting

#### Error: Elasticsearch 137

```commandline
ERROR: Elasticsearch exited unexpectedly, with exit code 137
```
This is caused by Elasticsearch not having enough memory.

Increase total memory available to 8gb.

```commandline
colima down
colima start --memory 8
```


#### Error: RabbitMQ permissions
```commandline
rabbitmq-1            | chown: /var/lib/rabbitmq: Permission denied
```

This is caused my rabbitmq not having access the volumes defined in docker-compose.yml.

First try running the following:

```commandline
chmod -R 777 ./data
chmod -R 777 ./infra
```

If this doesn't work then update the `rabbitmq` service in the `docker-compose.yml`
by adding a new `user` key so that the container assumes your own identity, i.e.:

```yaml
  rabbitmq:
    image: rabbitmq:3-management
    user: "{UID}:{GID}"
```

Where `UID` and `GID` can be found by running `id -u` and `id -g` respectively.

#### Error: Docker... no space left on device

```commandline
docker: /var/lib/... no space left on device
```

This is caused by your own laptop being too full to create a new image.

Clear out old docker artefacts:

```commandline
docker system prune --all --force
```
