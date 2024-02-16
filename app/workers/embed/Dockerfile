FROM python:3.11

ARG MODEL_NAMES=all-mpnet-base-v2|paraphrase-multilingual-MiniLM-L12-v2

RUN pip install poetry

COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root --no-ansi

ADD download_model.py /download_model.py
RUN mkdir models
RUN poetry run python download_model.py


ADD app.py /app.py

EXPOSE 5000

# Run FastAPI

CMD ["poetry", "run", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000"]