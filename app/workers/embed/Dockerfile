FROM python:3.12-slim

ARG MODEL_NAMES=all-mpnet-base-v2|paraphrase-multilingual-MiniLM-L12-v2

RUN pip install poetry

# Add redbox python package and install it with poetry
ADD redbox/ /app/redbox
ADD pyproject.toml poetry.lock /app/
WORKDIR /app/
RUN poetry install --no-root --no-ansi --with worker,embed

# Add the rest of the files
ADD ./app/workers/embed/app.py /app/
ADD ./app/workers/embed/download_model.py /app/

# Download the model
RUN poetry run python download_model.py

EXPOSE 5000

# Run FastAPI
CMD ["poetry", "run", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000"]
