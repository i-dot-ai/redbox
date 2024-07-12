FROM python:3.12-bookworm as builder

RUN apt-get update && apt-get install --yes build-essential curl > /dev/null

# Add redbox python package and install it with poetry
ADD redbox-core/ /app/redbox-core
ADD core-api/ /app/core-api
ADD README.md /app/README.md

WORKDIR /app/core-api

RUN pip install poetry
RUN poetry install

# Run FastAPI
EXPOSE 5002
CMD ["poetry", "run", "uvicorn", "core_api.app:app", "--host", "0.0.0.0", "--port", "5002"]
