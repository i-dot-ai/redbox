FROM python:3.11

RUN pip install poetry

COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root --no-ansi

WORKDIR /app

ADD app.py /app/

# Run FastAPI
EXPOSE 5001
CMD ["poetry", "run", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5001"]
