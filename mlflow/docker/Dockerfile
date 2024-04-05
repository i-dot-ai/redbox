# Use the MLFlow image as the base
FROM ghcr.io/mlflow/mlflow

WORKDIR /mlflow

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

CMD mlflow server --host 0.0.0.0 --port 5010