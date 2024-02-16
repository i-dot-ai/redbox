FROM python:3.11

RUN pip install poetry

COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root --no-ansi

RUN mkdir /celery_home/
ADD app/ /celery_home/app/
WORKDIR /celery_home/

# Run Celery
CMD ["poetry", "run", "celery",  "-A", "app", "worker", "-l", "INFO"]