FROM python:3.11

RUN pip install poetry

# Add redbox python package and install it with poetry
ADD redbox/ /app/redbox
ADD pyproject.toml poetry.lock /app/
WORKDIR /app/
RUN poetry install --no-root --no-ansi --with worker,ingest,embed --without ai,dev,api

ADD ./download_embedder.py /app/
# Download the model
RUN poetry run download-embedder

WORKDIR /app
ADD ./ingest/app.py /app/app.py

# Run pika worker
CMD ["poetry", "run", "python", "app.py"]
