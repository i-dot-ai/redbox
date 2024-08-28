from http import HTTPStatus

from fastapi.testclient import TestClient


def test_get_health(app_client: TestClient):
    """
    Given that the app is running
    When I call /health
    I Expect to see the docs
    """
    response = app_client.get("/health")
    assert response.status_code == HTTPStatus.OK
