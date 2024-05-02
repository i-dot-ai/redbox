FROM ghcr.io/mlflow/mlflow

WORKDIR /mlflow

COPY mlflow/docker/requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

COPY mlflow/config.yaml /root/.config/mlflow/config.yaml

# runs MLflow server connecting endpoint
RUN echo '#!/bin/bash' > /start.sh && \
    echo 'mlflow deployments start-server --config-path /root/.config/mlflow/config.yaml --port 5010 --host 0.0.0.0 &' >> /start.sh && \
    echo 'export MLFLOW_DEPLOYMENTS_TARGET="http://127.0.0.1:5010"' >> /start.sh && \
    echo 'mlflow server --port 5020 --host 0.0.0.0' >> /start.sh && \
    chmod +x /start.sh

CMD ["/start.sh"]
