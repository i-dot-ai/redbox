FROM python:3.11

RUN pip install poetry

# Add redbox python package and install it with poetry
ADD redbox/ /app/redbox
ADD pyproject.toml poetry.lock /app/
WORKDIR /app/
ADD ./download_embedder.py /app/
ADD ./model_db.py /app/
RUN poetry install --no-root --no-ansi --with worker,ingest,embed --without ai,dev,api

# Download the model
RUN poetry run download-model

WORKDIR /app
ADD ./ingest/src/app.py /app/app.py

# Run pika worker
CMD ["poetry", "run", "python", "app.py"]
