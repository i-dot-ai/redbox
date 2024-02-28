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
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN pip install poetry

COPY app/django_app/ /app/
COPY poetry.lock /app/poetry.lock
COPY pyproject.toml /app/pyproject.toml
COPY .env /app/app/django_app/
COPY .env.test /app/app/django_app/
WORKDIR app/
RUN poetry install --no-root --no-ansi --with redbox-core,dev --without ai,ingest,embed,worker

COPY app/django_app/docker/web/start.sh app/start.sh
RUN chmod +x app/start.sh

EXPOSE 8090
CMD ["sh", "app/django_app/docker/web/start.sh"]
