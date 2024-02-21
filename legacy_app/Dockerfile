FROM python:3.11

RUN apt-get update
RUN apt-get install -y libgl-dev libmagic-dev inetutils-ping

RUN pip install poetry

COPY redbox/pyproject.toml redbox/poetry.lock ./
RUN poetry install --no-root --no-ansi

ADD redbox/ /app/redbox
ADD download_embedder.py /app
ADD legacy_app /app

WORKDIR /app/

RUN poetry run python download_embedder.py

EXPOSE 8501

ENTRYPOINT ["poetry", "run", "streamlit", "run", "--server.address", "0.0.0.0", "--server.port", "8501", "Welcome.py" ]
