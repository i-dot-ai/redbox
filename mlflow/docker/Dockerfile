FROM ghcr.io/mlflow/mlflow

WORKDIR /mlflow

COPY mlflow/docker/requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* 

COPY mlflow/config.yaml /root/.config/mlflow/config.yaml

RUN echo '#!/bin/bash' > /start.sh && \
    echo 'mlflow deployments start-server --config-path /root/.config/mlflow/config.yaml --port 5010 --host 0.0.0.0 &' >> /start.sh && \
    echo 'export OPENAI_API_KEY="$OPENAI_API_KEY"' >> /start.sh && \
    echo 'export MLFLOW_DEPLOYMENTS_TARGET="http://127.0.0.1:5010"' >> /start.sh && \
    echo 'mlflow server --port 5020' >> /start.sh && \
    chmod +x /start.sh

CMD ["/start.sh"]