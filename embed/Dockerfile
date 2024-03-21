FROM python:3.11

RUN pip install poetry

# Add redbox python package and install it with poetry
ADD redbox/ /app/redbox

ADD pyproject.toml poetry.lock /app/
ADD ./download_embedder.py /app/
ADD ./model_db.py /app/
WORKDIR /app/
RUN poetry install --no-root --no-ansi --with worker,api --without ai,ingest,dev,pytest-django,streamlit-app

# Add the rest of the files
ADD ./embed/src/app.py /app/app.py

ADD ./Makefile /app/
ADD ./.env.example /app/

# Download the model
RUN poetry run download-model

EXPOSE 5000

CMD ["poetry", "run", "python", "app.py"]
