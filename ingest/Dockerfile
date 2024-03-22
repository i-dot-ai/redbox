FROM python:3.11

RUN pip install poetry

# Add redbox python package and install it with poetry
ADD redbox/ /app/redbox
ADD ingest/src/app.py /app/app.py
ADD pyproject.toml poetry.lock /app/

WORKDIR /app/
RUN poetry install --no-root --no-ansi --with worker,ingest --without ai,dev,api,django-app,pytest-django,streamlit-app
ADD ./.env /app/

# Download the model
RUN poetry run download-model

# Run pika worker
CMD ["poetry", "run", "python", "app.py"]
