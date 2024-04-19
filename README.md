# 📮 Redbox Copilot

> [!IMPORTANT]
> Incubation Project: This project is an incubation project; as such, we DON’T recommend using it in any critical use case. This project is in active development and a work in progress. This project may one day Graduate, in which case this disclaimer will be removed.

> [!NOTE]
> The original streamlit-app has moved to its own repository https://github.com/i-dot-ai/redbox-copilot-streamlit.

Redbox Copilot is a retrieval augmented generation (RAG) app that uses GenAI to chat with and summarise civil service documents. It's designed to handle a variety of administrative sources, such as letters, briefings, minutes, and speech transcripts.

- **Better retrieval**. Redbox Copilot increases organisational memory by indexing documents
- **Faster, accurate summarisation**. Redbox Copilot can summarise reports read months ago, supplement them with current work, and produce a first draft that lets civil servants focus on what they do best

# Setup

Please refer to the [DEVELOPER_SETUP.md](./docs/DEVELOPER_SETUP.md) for detailed instructions on setting up the project.

# Codespace
For a quick start, you can use GitHub Codespaces to run the project in a cloud-based development environment. Click the button below to open the project in a new Codespace.

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/i-dot-ai/redbox-copilot?quickstart=1)

# Development

You will need to install `poppler` and `tesseract` to run the `ingester`
- `brew install poppler`
- `brew install tesseract`

- Download and install [pre-commit](https://pre-commit.com) to benefit from pre-commit hooks
  - `pip install pre-commit`
  - `pre-commit install`

# Testing
- Unit tests and QA run in CI
- At this time integration test(s) take 10+ mins to run so are triggered manually in CI

# Dependencies

This project uses a microservice architecture.

Each microservice runs in its own container defined by a `Dockerfile`.

For every microservice that we have written in python we define its dependencies using https://python-poetry.org/.

This means that our project is structured approximately like this:

```txt
redbox-copilot/
├── frontend/
├── django_app
│  ├── app/
│  ├── static/
│  ├── tests/
│  ├── manage.py
│  └── Dockerfile
├── embedder
│  ├── src/
│  │  └── worker.py
│  ├── tests/
│  └── Dockerfile
├── ingester
│  ├── src/
│  │  └── worker.py
│  ├── tests/
│  └── Dockerfile
├── redbox/
│  ├── exceptions/
│  ├── export/
│  ├── llm/
│  ├── models/
│  ├── parsing/
│  ├── storage
│  ├── tests/
│  └── Dockerfile
├── docker-compose.yaml
├── pyproject.toml
├── Makefile
└── README.md
```

# Contributing

We welcome contributions to this project. Please see the [CONTRIBUTING.md](./CONTRIBUTING.md) file for more information.

# License

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details.

# Security

If you discover a security vulnerability within this project, please follow our [Security Policy](./SECURITY.md).

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

#### Error: Docker... no space left on device

```commandline
docker: /var/lib/... no space left on device
```

This is caused by your own laptop being too full to create a new image.

Clear out old docker artefacts:

```commandline
docker system prune --all --force
```

### Frontend


#### CSS

We depend on `govuk-frontend` for GOV.UK Design System styles.

```
npm install
```

Once this has been done, `django-compressor` should work automatically to
compile the govuk-frontend SCSS on the first request and any subsequent request
after the SCSS has changed. In the meantime it will read from `frontend/CACHE`,
which is `.gitignore`d.

When we get to production, we can prepopulate `frontend/CACHE` using `manage.py
compress` before building our container, which will mean that every request
will be served from the cache.

`django-compressor` also takes care of fingerprinting and setting cache headers
for our CSS so it can be cached.

#### Fonts and images

The govuk assets are versioned in the `npm` package. On initial app setup you will need to run `poetry run python manage.py collectstatic` to copy them to the `frontend` folder from where `runserver` can serve them.

We’ll revisit this process when we deploy the app.

