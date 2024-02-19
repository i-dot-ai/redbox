FROM python:3.11-slim

RUN apt-get update
RUN apt-get install -y libgl-dev libmagic-dev inetutils-ping

RUN pip install poetry

COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root --no-ansi

ADD redbox/ /app/redbox
ADD legacy_app /app

WORKDIR /app/

EXPOSE 8501

ENTRYPOINT ["poetry", "run", "streamlit", "run", "--server.address", "0.0.0.0", "--server.port", "8501", "Welcome.py" ]
