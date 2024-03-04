FROM python:3.11

RUN pip install poetry

# Add redbox python package and install it with poetry
ADD redbox/ /app/redbox

ADD pyproject.toml poetry.lock /app/
WORKDIR /app/
RUN poetry install --no-root --no-ansi --with worker,embed,api --without ai,ingest,dev

# Add the rest of the files
ADD ./embed /app/
ADD ./download_embedder.py /app/
ADD ./Makefile /app/
ADD ./.env.example /app/

# Download the model
RUN poetry run download-embedder

EXPOSE 5000

# Run FastAPI
CMD ["poetry", "run", "uvicorn", "embed.src:app", "--host", "0.0.0.0", "--port", "5000"]
