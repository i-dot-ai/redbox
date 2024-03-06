FROM python:3.11
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN pip install poetry

COPY django_app/ /app/
COPY poetry.lock /app/poetry.lock
COPY pyproject.toml /app/pyproject.toml
WORKDIR app/
RUN poetry install --no-root --no-ansi --with django-app,dev --without ai,ingest,embed,worker

COPY django_app/docker/web/start.sh app/start.sh
RUN chmod +x app/start.sh

EXPOSE 8090
CMD ["sh", "django_app/docker/web/start.sh"]
