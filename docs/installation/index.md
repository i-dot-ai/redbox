# Installation

## Step 1: **Requirements**

In this section we will cover some of the key dependencies for all of the deployment modes.

-  [Docker](https://docs.docker.com/get-docker/) - For building and running containers
-  [Docker Compose](https://docs.docker.com/compose/install/) - For managing multiple containers
-  [Python 3.12](https://www.python.org/downloads/) - For intellisense and linting (not explicitly needed to run the project due to docker, but recommended for development)
-  [pip](https://pip.pypa.io/en/stable/installation/) - For installing poetry
-  [poetry](https://python-poetry.org/docs/) - For managing python packages
-  [Make](https://www.gnu.org/software/make/) - For running commands in the `Makefile`
-  [Poppler](https://poppler.freedesktop.org/) - For Document Ingestion and OCR
-  [Tesseract](https://github.com/tesseract-ocr/tesseract) - For Document Ingestion and OCR


### Brew

If you're on a Mac, you can install the above dependencies using [brew](https://brew.sh/). 

```bash
brew install docker docker-compose python@3.12 make poppler tesseract
```

### Ubuntu/Debian

If you're on Ubuntu/Debian, you can install the above dependencies using `apt`.

```bash
sudo apt update
sudo apt install docker docker-compose python3.12 make poppler-utils tesseract-ocr
```

If you don't have this python version, we'd recommend using [pyenv](https://github.com/pyenv/pyenv) to manage your python versions.

## Step 2: **Installation and Build**

We'll need to clone the repository and install the dependencies.

```bash
git clone git@github.com:i-dot-ai/redbox.git
cd redbox
poetry install
```

This may take a while as it installs all the dependencies on a first run.

To build the project, you can use the following command:

```bash
make build
```

or 

```bash
docker compose build
```

At the end of the you can view all of the built images with this command:
    
```bash
docker images | grep redbox
```

## Step 3: **Setting up the environment**

The project uses a `.env` file to store environment variables. You can copy the `.env.example` file to `.env` and fill in the necessary variables.

```bash
cp .env.example .env
```

Depending on the Large Language Model provider you choose, you will need to fill appropriate API keys in the `.env` file. You can find more detail on that here: [LLM Setup](./llm_setup.md)


## Step 4: **Running the project**

From this point you can now go to the following pages to run the project:

- [Local Development](./local.md)
- [AWS Deployment](./aws.md)

At the moment, we only support local development and AWS deployment due to the skillsets of the current development team. Redbox would welcome any contributions to help expand deployments to Azure, GCP, Orcacle Cloud, Kubernetes, etc. If you would like to add support for a new deployment mode please refer to the [contribution guidelines](./CONTRIBUTING.md) and create a pull request with the necessary changes. Please refer to the email link in the footer if you'd like to discuss with the team.
