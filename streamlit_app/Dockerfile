FROM python:3.11

RUN apt-get update
RUN apt-get install -y libgl-dev libmagic-dev inetutils-ping

RUN pip install poetry

WORKDIR /app/

ADD pyproject.toml poetry.lock ./
# Streamlit app needs a lot of dependencies
ADD ./download_embedder.py /app/
ADD ./model_db.py /app/
RUN poetry install --no-root --no-ansi --with streamlit-app,ai,ingest --without dev,worker,api,pytest-django

ADD redbox/ /app/redbox
ADD streamlit_app/ /app

# Download the model

RUN poetry run download-model

EXPOSE 8501

ENTRYPOINT ["poetry", "run", "streamlit", "run", "--server.address", "0.0.0.0", "--server.port", "8501", "Welcome.py" ]
