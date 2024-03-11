FROM python:3.11
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN pip install poetry

# Install node for nvm command
ENV NODE_VERSION=20.11.1
RUN apt install -y curl
RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
ENV NVM_DIR=/root/.nvm
RUN . "$NVM_DIR/nvm.sh" && nvm install ${NODE_VERSION}
RUN . "$NVM_DIR/nvm.sh" && nvm use v${NODE_VERSION}
RUN . "$NVM_DIR/nvm.sh" && nvm alias default v${NODE_VERSION}
ENV PATH="/root/.nvm/versions/node/v${NODE_VERSION}/bin/:${PATH}"
RUN node --version
RUN npm --version

COPY django_app/ /app/
COPY poetry.lock /app/poetry.lock
COPY pyproject.toml /app/pyproject.toml

WORKDIR app/django_app/
RUN npm install

WORKDIR app/
RUN poetry install --no-root --no-ansi --with django-app,dev,pytest-django --without ai,ingest,embed,worker

COPY django_app/docker/web/start.sh app/start.sh
RUN chmod +x app/start.sh

EXPOSE 8090
CMD ["sh", "django_app/docker/web/start.sh"]
