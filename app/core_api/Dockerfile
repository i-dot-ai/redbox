FROM python:3.11

RUN pip install poetry

# Add redbox python package and install it with poetry
ADD redbox/ /app/redbox
ADD pyproject.toml poetry.lock /app/
WORKDIR /app/
RUN poetry install --no-root --no-ansi --with api

WORKDIR /app

ADD app/core_api/app.py /app/

# Run FastAPI
EXPOSE 5002
CMD ["poetry", "run", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5002"]
