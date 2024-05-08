import logging
import os
import uuid
from datetime import datetime

import pytest
import pytz
from redbox_app.redbox_core import client
from redbox_app.redbox_core.models import ChatHistory, User

UTC = pytz.timezone("UTC")

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


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


@pytest.fixture
def file_pdf_path():
    path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "data",
        "pdf",
        "Cabinet Office - Wikipedia.pdf",
    )
    yield path


@pytest.fixture
def file_py_path():
    path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "data",
        "py",
        "test_data.py",
    )
    yield path


@pytest.fixture
def s3_client():
    yield client.s3_client()


@pytest.fixture
def chat_history(alice: User) -> ChatHistory:
    session_id = uuid.uuid4()
    logger.debug(f"{session_id=}")
    chat_history = ChatHistory.objects.create(id=session_id, users=alice)
    yield chat_history
    chat_history.delete()
