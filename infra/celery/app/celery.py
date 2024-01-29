from celery import Celery
from celery.backends.elasticsearch import ElasticsearchBackend

app = Celery(
    "redbox-tasks",
    broker="amqp://guest@rabbitmq:5672//",
    include=["app.workers"],
    broker_connection_retry_on_startup=True,
)

backend = ElasticsearchBackend(
    app=app, host="elasticsearch", port=9200, username="elastic", password="redboxpass"
)
