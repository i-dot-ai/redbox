import logging
import string
import subprocess
from pathlib import Path
from random import choice

import pytest
from pages import LandingPage, SignInConfirmationPage
from playwright.sync_api import Page
from yarl import URL

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

BASE_URL = URL("http://localhost:8090/")
TEST_ROOT = Path(__file__).parent


def test_user_journey(page: Page, email_address: str):
    create_user(email_address)

    # Landing page
    landing_page = LandingPage(page, BASE_URL)

    # Sign in
    sign_in_page = landing_page.navigate_to_sign_in()
    sign_in_page.email = email_address
    sign_in_page.continue_()

    # Use magic link
    magic_link = get_magic_link(email_address)
    logger.debug("magic_link: %s", magic_link)
    sign_in_confirmation_page = SignInConfirmationPage(page, magic_link)

    # Documents page
    documents_page = sign_in_confirmation_page.navigate_to_documents_page()
    document_rows = documents_page.get_all_document_rows()
    original_docs_count = len(document_rows)

    # Upload a file
    document_upload_page = documents_page.navigate_to_upload()
    upload_file = TEST_ROOT / "data" / "pdf" / "Cabinet Office - Wikipedia.pdf"
    documents_page = document_upload_page.upload_document(upload_file)
    document_rows = documents_page.get_all_document_rows()
    logger.debug("document_rows: %s", document_rows)
    assert any(row.filename == upload_file.name for row in document_rows)
    assert len(document_rows) == original_docs_count + 1

    # Delete a file
    document_delete_page = documents_page.delete_latest_document()
    documents_page = document_delete_page.confirm_deletion()
    document_rows = documents_page.get_all_document_rows()
    assert len(document_rows) == original_docs_count

    # Chats page
    chats_page = documents_page.navigate_to_chats()
    chats_page.write_message = "What is the Cabinet Office?"
    chats_page = chats_page.send()
    all_messages = chats_page.all_messages()
    logger.debug("page: %s", chats_page)
    logger.debug("all_messages: %s", all_messages)


def test_support_pages(page: Page):
    # Landing page
    landing_page = LandingPage(page, BASE_URL)

    # Privacy page
    landing_page.navigate_to_privacy_page()

    # Accessibility page
    landing_page.navigate_to_accessibility_page()

    # Support page
    landing_page.navigate_to_support_page()


def create_user(email_address: str):
    command = [
        "docker",
        "compose",
        "run",
        "django-app",
        "venv/bin/django-admin",
        "createsuperuser",
        "--noinput",
        "--email",
        email_address,
    ]
    result = subprocess.run(command, capture_output=True, text=True)  # noqa: S603
    result.check_returncode()
    logger.debug("create_user result: %s", result)


def get_magic_link(email_address: str) -> URL:
    command = ["docker", "compose", "run", "django-app", "venv/bin/django-admin", "show_magiclink_url", email_address]
    result = subprocess.run(command, capture_output=True, text=True)  # noqa: S603
    result.check_returncode()
    magic_link = result.stdout.strip().lstrip("/")
    return BASE_URL / magic_link


@pytest.fixture()
def email_address() -> str:
    username = "".join(choice(string.ascii_lowercase) for _ in range(10))  # noqa: S311
    return f"{username}@cabinetoffice.gov.uk"
