FROM ghcr.io/mlflow/mlflow

WORKDIR /mlflow

COPY mlflow/requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

COPY mlflow/config.yaml /root/.config/mlflow/config.yaml

# runs MLflow server connecting endpoint
CMD mlflow deployments start-server --config-path /root/.config/mlflow/config.yaml --port 5010 --host 0.0.0.0 & \
    export MLFLOW_DEPLOYMENTS_TARGET="http://127.0.0.1:5010" && \
    mlflow server --port 5020 --host 0.0.0.0
