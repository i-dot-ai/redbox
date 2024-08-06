FROM python:3.12-bookworm as builder


RUN pip install poetry

ADD redbox-core/ /app/redbox-core
ADD worker/ /app/worker
ADD README.md /app/README.md

WORKDIR /app/worker

RUN poetry install


RUN chmod +x health.sh

CMD ["poetry", "run", "faststream", "run", "worker.app:app"]
