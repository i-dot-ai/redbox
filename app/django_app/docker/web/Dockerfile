#FROM python:3.11.6
#ENV PYTHONDONTWRITEBYTECODE 1
#ENV PYTHONUNBUFFERED 1
#
#WORKDIR /app
#
#COPY . /app
#
#RUN python3 -m pip install poetry
#RUN poetry install
#
#COPY ./docker/web/start.sh /start.sh
#RUN chmod +x /start.sh
#
#EXPOSE 8090
#
#CMD ["sh", "/start.sh"]

FROM python:3.11

RUN pip install poetry

COPY app/django_app/ /app/
COPY poetry.lock /app/poetry.lock
COPY pyproject.toml /app/pyproject.toml
COPY .env /app/.env
COPY .env.test /app/.env.test
WORKDIR /app/
RUN poetry install --no-root --no-ansi --with redbox-core --without ai,ingest,embed,dev,worker

COPY app/django_app/docker/web/start.sh /app/start.sh
RUN chmod +x /app/start.sh

EXPOSE 8090
CMD ["sh", "app/django_app/docker/web/start.sh"]
