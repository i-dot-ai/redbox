# 📮 Redbox Copilot

Redbox Copilot is a retrieval augmented generation (RAG) app that uses Claude 2 to organise, categorise and summarise civil service documents. It's designed to handle a variety of administrative sources, such as letters, briefings, minutes, and speech transcripts.

* **Better retrieval**. Redbox Copilot increases organisational memory by indexing documents
* **Faster, accurate summarisation**. Redbox Copilot can summarise reports read months ago, supplement them with current work, and produce a first draft that lets civil servants focus on what they do best

# Codespace

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/i-dot-ai/redbox-copilot?quickstart=1)

# Setup

* Ensure Python 3.9+ is installed
* Create a `.env` with `cp .env.example .env` and add the relevant API keys and settings
* Create the Python virtual environment with `make venv`
* Run the app with `make app`

# Development

* Download and install [pre-commit](https://pre-commit.com) to benefit from pre-commit hooks
    * `pip install pre-commit`
    * `pre-commit install`
