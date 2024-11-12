[![Integration Tests](https://github.com/i-dot-ai/redbox/actions/workflows/integration.yml/badge.svg?branch=main)](https://github.com/i-dot-ai/redbox/actions/workflows/integration.yml?query=branch%3Amain)

# 📮 Redbox

> [!IMPORTANT]
> Incubation Project: This project is an incubation project; as such, we DON’T recommend using it in any critical use case. This project is in active development and a work in progress. This project may one day Graduate, in which case this disclaimer will be removed.

> [!NOTE]
> The original streamlit-app has moved to its own repository https://github.com/i-dot-ai/redbox-copilot-streamlit.

Redbox is a retrieval augmented generation (RAG) app that uses GenAI to chat with and summarise civil service documents. It's designed to handle a variety of administrative sources, such as letters, briefings, minutes, and speech transcripts.

- **Better retrieval**. Redbox increases organisational memory by indexing documents
- **Faster, accurate summarisation**. Redbox can summarise reports read months ago, supplement them with current work, and produce a first draft that lets civil servants focus on what they do best

https://github.com/i-dot-ai/redbox-copilot/assets/8233643/e7984242-1403-4c93-9e68-03b3f065b38d

# Setup

Please refer to the [DEVELOPER_SETUP.md](./docs/DEVELOPER_SETUP.md) for detailed instructions on setting up the project.

# Codespace

For a quick start, you can use GitHub Codespaces to run the project in a cloud-based development environment. Click the button below to open the project in a new Codespace.

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/i-dot-ai/redbox-copilot?quickstart=1)

# Development

Download and install [pre-commit](https://pre-commit.com) to benefit from pre-commit hooks

- `pip install pre-commit`
- `pre-commit install`

# Testing

- Unit tests and QA run in CI
- At this time integration test(s) take 10+ mins to run so are triggered manually in CI
- Run `make help` to see all the available build activities.

# Dependencies

This project is in two parts:

- A https://langchain-ai.github.io/langgraph/ based AI class library called redbox-core
- A django app to expose redbox-core to users over the web

The project is structured approximately like this:

```txt
redbox/
├── django_app
│  ├── redbox_app/
│  ├── static/
│  ├── tests/
│  ├── manage.py
│  ├── pyproject.toml
│  └── Dockerfile
├── redbox-core/
│  ├── redbox
│  │  ├── api/
│  │  ├── chains/
│  │  ├── graph/
│  │  ├── loader/
│  │  ├── models/
│  │  ├── retriever/
│  │  └── storage/
│  ├── tests/
│  ├── pyproject.toml
│  └── Dockerfile
├── docker-compose.yaml
├── pyproject.toml
├── Makefile
└── README.md
```

## Configuration

System-wide, static, settings are defined [Settings.py](redbox-core/redbox/models/settings.py), these are set via environment file .env

Dynamic, per-request, settings are defined in [AISettings.py](redbox-core/redbox/models/chain.py), these are set within the django-app,
and can be changed by an administrator. This includes the LLM to use which by default will be GPT-4o.

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

To build the frontend assets, from the `django_app/frontend/` folder run:

```
npm install
```

Then, for a one-off build run:

```
npx parcel build
```

Or, to watch for changes (e.g. if making CSS and JS changes):

```
npx parcel watch
```

On initial app setup you will need to run `poetry run python manage.py collectstatic` to copy them to the `frontend` folder from where `runserver` can serve them. Or you can run `make build-django-static` which combines the parcel build and collectstatic commands.

#### Testing

To run the web-component tests, from the frontend folder run:

```
npm run test
```

## How to deploy

checkout the `main` branch of the following repos:

- https://github.com/i-dot-ai/redbox
- https://github.com/i-dot-ai/redbox-copilot-infra-config

Replace `var.image_tag` in `infrastructure/aws/ecs.tf` with the hash of the build you want deployed. Make sure that the hash corresponds to an image that exists in ECR,
if in doubt build it via the [build-action](./.github/workflows/build.yaml).

Login to aws via `aws-vault exec admin-role` and run the commands below from the redbox repo root

```commandline
make tf_init env=<ENVIRONMENT>
make tf_apply env=<ENVIRONMENT>
```

where ENVIRONMENT is one of `dev`, `preprod` or `prod`

## How to set up scheduled tasks

The django-app uses django-q to schedule task, this includes management tasks.
Follow the instructions here https://django-q2.readthedocs.io/en/master/schedules.html#management-commands, i.e.

1. navigate the admin / Scheduled Tasks / Add Scheduled Task
2. name = `delete old files`
3. func = `django.core.management.call_command`
4. args = `"delete_expired_data"`
5. save

## Vector databases

We are currently using ElasticSearch as our vector database.

We have also successfully deployed Redbox to OpenSearch Serverless but this support should be considered experimental
at this stage.
