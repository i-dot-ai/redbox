from threading import Event

import pytest
from elasticsearch import NotFoundError

from core_api.src.app import env


def test_get_health(app_client):
    """
    Given that the app is running
    When I call /health
    I Expect to see the docs
    """
    response = app_client.get("/health")
    assert response.status_code == 200


def test_post_file_upload(s3_client, app_client, elasticsearch_storage_handler, bucket, file_pdf_path):
    """
    Given a new file
    When I POST it to /file
    I Expect to see it persisted in s3 and elastic-search
    """
    with open(file_pdf_path, "rb") as f:
        response = app_client.post("/file", files={"file": ("filename", f, "pdf")})
    assert response.status_code == 200
    assert s3_client.get_object(Bucket=bucket, Key=file_pdf_path.split("/")[-1])
    json_response = response.json()
    assert elasticsearch_storage_handler.read_item(
        item_uuid=json_response["uuid"], model_type=json_response["model_type"]
    )


def test_get_file(app_client, stored_file):
    """
    Given a previously saved file
    When I GET it from /file/uuid
    I Expect to receive it
    """

    response = app_client.get(f"/file/{stored_file.uuid}")
    assert response.status_code == 200


def test_delete_file(s3_client, app_client, elasticsearch_storage_handler, bucket, stored_file):
    """
    Given a previously saved file
    When I DELETE it to /file
    I Expect to see it removed from s3 and elastic-search
    """
    # check assets exist
    assert s3_client.get_object(Bucket=bucket, Key=stored_file.name)
    assert elasticsearch_storage_handler.read_item(item_uuid=stored_file.uuid, model_type="file")

    response = app_client.delete(f"/file/{stored_file.uuid}")
    assert response.status_code == 200

    # check assets dont exist
    with pytest.raises(Exception):
        s3_client.get_object(Bucket=bucket, Key=stored_file.name)

    with pytest.raises(NotFoundError):
        elasticsearch_storage_handler.read_item(item_uuid=stored_file.uuid, model_type="file")


def test_ingest_file(app_client, rabbitmq_channel, stored_file):
    """
    Given a previously saved file
    When I POST to /file/uuid/ingest
    I Expect to see a message on the ingest-queue, THIS IS NOT WORKING
    """
    message_consumed = Event()

    def callback(ch, method, properties, body):
        message_consumed.set()
        ch.basic_ack(delivery_tag=method.delivery_tag)

    rabbitmq_channel.basic_consume(queue=env.ingest_queue_name, on_message_callback=callback)

    response = app_client.post(f"/file/{stored_file.uuid}/ingest/")
    assert response.status_code == 200

    # TODO: fix this!
    # start_time = time.time()
    # while not message_consumed.is_set() and time.time() - start_time < 10:
    #     time.sleep(0.1)
    #
    # assert message_consumed.is_set()
    # rabbitmq_channel.basic_cancel(consumer_tag=None)
