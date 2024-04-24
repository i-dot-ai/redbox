# Developer Setup Guide

## Requirements

To run this project, you'll need the following installed:

-  [Docker](https://docs.docker.com/get-docker/) - For building and running containers
-  [Docker Compose](https://docs.docker.com/compose/install/) - For managing multiple containers
-  [Python 3.11](https://www.python.org/downloads/) - For intellisense and linting (not explicitly needed to run the project due to docker, but recommended for development)
-  [pip](https://pip.pypa.io/en/stable/installation/) - For installing poetry
-  [poetry](https://python-poetry.org/docs/) - For managing python packages
-  [Make](https://www.gnu.org/software/make/) - For running commands in the `Makefile`

If you don't have this python version, we'd recommend using [pyenv](https://github.com/pyenv/pyenv) to manage your python versions.

## Installing packages

Currently, we use [poetry](https://python-poetry.org/) to manage our python packages. The list of poetry groups and python packages we install can be found [here](https://github.com/i-dot-ai/redbox-copilot/blob/main/pyproject.toml) in `pyproject.toml`.

Run the following to install the packages into a virtual environment poetry will create.

``` bash
poetry install
```

## Setting environment variables

We use `.env` files to populate the environment variables for local development. When cloning the repository the files `.env.test`, `.env.django`, `.env.integration` and `.env.example` will be populated.

To run the project, create a new file called `.env` and populate this file with the setting names from `.env.example` and the values these settings need.

Typically this involves setting the following variables:

- `OPENAI_API_KEY` - OpenAI API key
- `ANTHROPIC_API_KEY` - Anthropic API key

**`.env` is in `.gitignore` and should not be committed to git**

## Other dependencies (for Document Ingestion and OCR)

You will need to install `poppler` and `tesseract` to run the `worker`
- `brew install poppler`
- `brew install tesseract`



## Building and running the project

To view all the build commands, check the `Makefile` that can be found [here](https://github.com/i-dot-ai/redbox-copilot/blob/main/Makefile).

The project currently consists of multiple docker images needed to run the project in its entirety. If you only need a subsection of the project running, for example if you're only editing the django app, you can run a subset of the images. The images currently in the project are:

- `elasticsearch`
- `kibana`
- `worker`
- `minio`
- `redis`
- `core-api`
- `db`
- `django-app`

To build the images needed to run the project, use this command:

``` bash
make build
```

or 

``` bash
docker compose build
```

Once those images have built, you can run them using:

``` bash
make run
```

or 

``` bash
docker compose up
```

Some parts of the project can be run independently for development, for example the django application, which can be run with:

``` bash
docker compose up django-app
```

For any other commands available, check the `Makefile` [here](https://github.com/i-dot-ai/redbox-copilot/blob/main/Makefile).

## How to run tests

Tests are split into different commands based on the application the tests are for. For each application there is a separate `make` command to run those tests, these are:

For the django app:

``` bash
make test-django
```

For the core API:

``` bash
make test-core-api
```

For the worker:

``` bash
make test-worker
```

For integration tests:

``` bash
make test-integration
```

## Pre-commit hooks

- Download and install [pre-commit](https://pre-commit.com) to benefit from pre-commit hooks
  - `pip install pre-commit`
  - `pre-commit install`