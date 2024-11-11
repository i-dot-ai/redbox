# Developer Setup Guide

## Requirements


## Installing packages

Currently, we use [poetry](https://python-poetry.org/) to manage our python packages. There are 3 `pyproject.toml`s 
- [redbox-core](https://github.com/i-dot-ai/redbox/blob/main/redbox-core/pyproject.toml) - core AI package
- [django-app](https://github.com/i-dot-ai/redbox/blob/main/django_app/pyproject.toml) - django webserver and background worker
- [root](https://github.com/i-dot-ai/redbox/blob/main/pyproject.toml) - Integration tests, QA, and docs


## VSCode
To make use of the VSCode setup open the workspace file .vscode/redbox.code-workspace. This will open the relevant services as roots in a single workspace. The recommended way to use this is:
* Create a venv in each of the main service directories (redbox-core, django-app) this should be in a directory called _venv_
* Configure each workspace directory to use it's own venv python interpreter. NB You may need to enter these manually when prompted as _./venv/bin/python_

The tests should then all load separately and use their own env.

## Setting environment variables

We use `.env` files to populate the environment variables for local development. When cloning the repository the file `.env.example` will be populated.

To run the project, create a new file called `.env` and populate this file with the setting names from `.env.example` and the values these settings need.

Typically this involves setting the following variables:

- `AZURE_OPENAI_API_KEY` - Azure OpenAI API key
- `AZURE_OPENAI_ENDPOINT` - Azure OpenAI API key
- `OPENAI_API_VESION` - OpenAI API version

It is best to leave hostnames out of the .env file. These are then set manually by vscode tasks or pulled from a deployment .env like .env.test/.env.integration

### Backend Profiles
Redbox can use different backends for chat and embeddings, which are used is controlled by env vars. The defaults are currently to use Azure for both chat and embeddings but OpenAI can be used (and pointed to an OpenAI compliant local service).
The relevant env vars for overriding to use OpenAI embeddings are:
- `EMBEDDING_AZURE_OPENAI_ENDPOINT` - usually the same as one of your `AZURE_OPENAI_ENDPOINT_XX`
- `EMBEDDING_OPENAI_KEY` - usually the same  as one of your `AZURE_OPENAI_API_KEY_XX`



**`.env` is in `.gitignore` and should not be committed to git**



## Building and running the project

To view all the build commands, check the `Makefile` that can be found [here](https://github.com/i-dot-ai/redbox/blob/main/Makefile).

The project currently consists of multiple docker images needed to run the project in its entirety. If you only need a subsection of the project running, for example if you're only editing the django app, you can run a subset of the images. The images currently in the project are:

- `elasticsearch`
- `minio`
- `db`
- `django-app`
- `worker`

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

For any other commands available, check the `Makefile` [here](https://github.com/i-dot-ai/redbox/blob/main/Makefile).

## How to run tests

Tests are split into different commands based on the application the tests are for. For each application there is a separate `make` command to run those tests, these are:

For the django app:

``` bash
make test-django
```

For the core AI:

``` bash
make test-redbox-core
```

For integration tests:

``` bash
make test-integration
```

## Logging in to Redbox Locally

We'll need to create a superuser to log in to the Django app, to do this run the following steps:

1. Come up with an email to log in with. It doesn't need to be real.
2. `docker compose run django-app venv/bin/django-admin createsuperuser`
3. Use the email you came up with in step 1, and a password (the password isn't used as we use magic links).
4. Now go to http://localhost:8090/sign-in/ enter the email you just created a super user for.
5. Press "Continue"
6. Now go to your terminal and run `docker compose logs django-app | grep 8090/magic_link`
7. Click that link and you should be logged in.


## Pre-commit hooks

- Download and install [pre-commit](https://pre-commit.com) to benefit from pre-commit hooks
  - `pip install pre-commit`
  - `pre-commit install`

## LLM evaluation

Notebooks with some standard methods to evaluate the LLM can be found in the [notebooks/](../notebooks/) directory.

You may want to evaluate using versioned datasets in conjunction with a snapshot of the pre-embedded vector store.

We use [elasticsearch-dump](https://github.com/elasticsearch-dump/elasticsearch-dump) to save and load bulk data from the vector store.

### Installing Node and `elasticsearch-dump`

Install [Node and `npm`](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm) (Node package manager) if you don't already have them. We recommend using [`nvm`](https://github.com/nvm-sh/nvm?tab=readme-ov-file#installing-and-updating) (Node version manager) to do this. 

If you're familiar with Node or use it regularly we recommend following your own processes or the tools' documentation. We endeavour to provide a quickstart here which will install `nvm`, Node, `npm` and `elasticsearch-dump` globally. This is generally not good practise.

To install `nvm`:

```console
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
```

Restart your terminal.

Install Node.

```console
nvm install node
nvm use --lts
```

Verify installation.

```console
node --version
```

Install `elasticsearch-dump` globally.

```console
npm install elasticdump -g
```

### Dumping data from Elasticsearch

The default indicex we want is `redbox-data-chunk`

Dump these to [data/elastic-dumps/](../data/elastic-dumps/) for saving or sharing.

```console
elasticdump \
  --input=http://localhost:9200/redbox-data-chunk \
  --output=./data/elastic-dumps/redbox-data-chunk.json \
  --type=data
```

### Loading data to Elasticsearch

If you've been provided with a dump from the vector store, add it to [data/elastic-dumps/](../data/elastic-dumps/). The below assumes the existance of `redbox-data-chunk.json` in that directory.

Consider dumping your existing indices if you don't want to have to reembed data you're working on.

Start the Elasticsearch service.

```console
docker compose up -d elasticsearch
```

Load data from your JSONs, or your own file.

```console
elasticdump \
  --input=./data/elastic-dumps/redbox-data-chunk.json \
  --output=http://localhost:9200/redbox-data-chunk \
  --type=data
```

If you're using this index in the frontend, you may want to upload the raw files to MinIO, though that's out of scope for this guide.
