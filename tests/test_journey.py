import logging
import os
import subprocess
from pathlib import Path

from playwright.sync_api import Page
from tests_playwright.pages import LandingPage, SignInConfirmationPage
from yarl import URL

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

BASE_URL = URL("http://localhost:8090/")
EMAIL_ADDRESS = "alice@cabinetoffice.gov.uk"
TEST_ROOT = Path(__file__)


def test_user_journey(page: Page):
    create_user(EMAIL_ADDRESS)

    # Landing page
    landing_page = LandingPage(page)

    # Sign in
    sign_in_page = landing_page.navigate_to_sign_in()
    sign_in_page.email = EMAIL_ADDRESS
    sign_in_page.continue_()

    # Use magic link
    magic_link = get_magic_link(EMAIL_ADDRESS)
    sign_in_confirmation_page = SignInConfirmationPage(page, magic_link)

    # Documents page
    documents_page = sign_in_confirmation_page.navigate_to_documents_page()
    document_upload_page = documents_page.navigate_to_upload()

    # Upload a file
    upload_file = TEST_ROOT / "data" / "pdf" / "Cabinet Office - Wikipedia.pdf"
    documents_page = document_upload_page.upload_document(upload_file)

    document_rows = documents_page.get_all_document_rows()
    logger.debug("document_rows: %s", document_rows)
    assert any(row.filename == upload_file.name for row in document_rows)

    # Chats page
    chats_page = documents_page.navigate_to_chats()
    chats_page.write_message = "What is the Cabinet Office?"
    chats_page = chats_page.send()
    all_messages = chats_page.all_messages()
    logger.debug("page: %s", chats_page)
    logger.debug("all_messages: %s", all_messages)


def test_support_pages(page: Page):
    # Landing page
    landing_page = LandingPage(page)

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
        "poetry",
        "run",
        "python",
        "manage.py",
        "createsuperuser",
        "--noinput",
    ]
    env = os.environ.copy()
    env["DJANGO_SUPERUSER_EMAIL"] = email_address
    env["DJANGO_SUPERUSER_USERNAME"] = email_address
    env["DJANGO_SUPERUSER_PASSWORD"] = email_address
    subprocess.run(command, capture_output=True, text=True, env=env)  # noqa: S603


def get_magic_link(email_address: str) -> URL:
    command = [
        "docker",
        "compose",
        "run",
        "django-app",
        "poetry",
        "run",
        "python",
        "manage.py",
        "show_magiclink_url",
        email_address,
    ]
    result = subprocess.run(command, capture_output=True, text=True)  # noqa: S603
    magic_link = result.stdout.strip().lstrip("/")
    return BASE_URL / magic_link
