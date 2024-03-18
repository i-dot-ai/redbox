FROM python:3.11

RUN pip install poetry

# Optimise image size with poetry by defining cache dir to be deleted after installation
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Add redbox python package and install it with poetry
ADD redbox/ /app/redbox

ADD pyproject.toml poetry.lock /app/
ADD ./download_embedder.py /app/
ADD ./model_db.py /app/
WORKDIR /app/

# Install the dependencies (with necessary dependency groups) and remove the cache dir (to reduce image size)
RUN poetry install --no-root --no-ansi --with worker,embed,api --without ai,ingest,dev

# Add the rest of the files
ADD ./embed/src/app.py /app/app.py

ADD ./Makefile /app/
ADD ./.env.example /app/

# Download the model
RUN poetry run download-model

EXPOSE 5000

# Run FastAPI
CMD ["poetry", "run", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000"]
