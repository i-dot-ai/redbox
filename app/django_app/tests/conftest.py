from datetime import datetime

import pytest
import pytz
from django.contrib.auth.models import User

UTC = pytz.timezone("UTC")


@pytest.fixture
def create_user():
    def _create_user(email, date_joined_iso):
        date_joined = UTC.localize(datetime.fromisoformat(date_joined_iso))
        user = User.objects.create_user(email=email, date_joined=date_joined)
        return user

    return _create_user


@pytest.fixture
def alice(create_user):
    return create_user("alice@cabinetoffice.gov.uk", "2000-01-01")


@pytest.fixture
def bob(create_user):
    return create_user("bob@example.com", "2000-01-01")


@pytest.fixture
def chris(create_user):
    return create_user("chris@example.com", "2000-01-02")


@pytest.fixture
def peter_rabbit(create_user):
    user = User.objects.create_user(email="peter.rabbit@example.com", password="P455W0rd")
    yield user


@pytest.fixture
def jemima_puddleduck():
    user = User.objects.create_user(email="jemima.puddleduck@example.com", password="P455W0rd")
    yield user


@pytest.fixture
def mrs_tiggywinkle():
    user = User.objects.create_user(email="mrs.tiggywinkle@example.com")
    yield user
