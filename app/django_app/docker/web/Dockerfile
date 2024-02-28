FROM python:3.11.6
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

COPY . /app

RUN python3 -m pip install poetry
RUN poetry install

COPY ./docker/web/start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 8090

CMD ["sh", "/start.sh"]
