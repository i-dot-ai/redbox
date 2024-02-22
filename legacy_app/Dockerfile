FROM python:3.11

RUN apt-get update
RUN apt-get install -y libgl-dev libmagic-dev inetutils-ping

RUN pip install poetry

ADD pyproject.toml poetry.lock ./
# Streamlit app needs a lot of dependencies
RUN poetry install --no-root --no-ansi --with streamlit-app,ai,ingest,embed --without dev,worker,api

ADD redbox/ /app/redbox
ADD legacy_app /app

WORKDIR /app/

EXPOSE 8501

ENTRYPOINT ["poetry", "run", "streamlit", "run", "--server.address", "0.0.0.0", "--server.port", "8501", "Welcome.py" ]
