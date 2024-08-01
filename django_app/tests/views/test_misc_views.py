import json
import logging
from http import HTTPStatus

import pytest
from django.conf import Settings
from django.test import Client
from yarl import URL

from redbox_app.redbox_core.models import User

logger = logging.getLogger(__name__)


@pytest.mark.django_db()
def test_declaration_view_get(peter_rabbit: User, client: Client):
    client.force_login(peter_rabbit)
    response = client.get("/")
    assert HTTPStatus(response.status_code).is_success
    assert response.headers["Cache-control"] == "no-store"
    assert "Report-To" not in response.headers


@pytest.mark.django_db()
def test_declaration_view_get_with_sentry_security_header_endpoint(
    peter_rabbit: User, client: Client, settings: Settings
):
    settings.SENTRY_REPORT_TO_ENDPOINT = URL("http://example.com")
    client.force_login(peter_rabbit)
    response = client.get("/")
    assert HTTPStatus(response.status_code).is_success
    assert json.loads(response.headers["Report-To"]) == {
        "group": "csp-endpoint",
        "max_age": 10886400,
        "endpoints": [{"url": "http://example.com"}],
        "include_subdomains": True,
    }
