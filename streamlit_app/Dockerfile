FROM python:3.11

RUN apt-get update
RUN apt-get install -y libgl-dev libmagic-dev inetutils-ping

RUN pip install poetry

# Optimise image size with poetry by defining cache dir to be deleted after installation
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /app/

ADD pyproject.toml poetry.lock ./

ADD ./download_embedder.py /app/
ADD ./model_db.py /app/

# Install the dependencies (with necessary dependency groups) and remove the cache dir (to reduce image size)
RUN poetry install --no-root --no-ansi --with streamlit-app,ai,ingest,embed --without dev,worker,api && rm -rf $POETRY_CACHE_DIR

ADD redbox/ /app/redbox
ADD streamlit_app/ /app

# Download the model

RUN poetry run download-model

EXPOSE 8501

ENTRYPOINT ["poetry", "run", "streamlit", "run", "--server.address", "0.0.0.0", "--server.port", "8501", "Welcome.py" ]
