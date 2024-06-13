import logging
import string
import subprocess
from pathlib import Path
from random import choice
from typing import TYPE_CHECKING

import pytest
from pages import LandingPage, SignInConfirmationPage
from playwright.sync_api import Page
from yarl import URL

if TYPE_CHECKING:
    from collections.abc import Sequence

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
    original_doc_count = documents_page.document_count()

    # Upload files
    document_upload_page = documents_page.navigate_to_upload()
    upload_files: Sequence[Path] = list(TEST_ROOT.parent.glob("*.md"))
    documents_page = document_upload_page.upload_documents(upload_files)
    document_rows = documents_page.all_documents
    assert {r.filename for r in document_rows} == {f.name for f in upload_files}
    assert documents_page.document_count() == original_doc_count + len(upload_files)
    documents_page.wait_for_documents_to_complete()

    # Chats page
    chats_page = documents_page.navigate_to_chats()
    chats_page.write_message = "What architecture is in use?"
    chats_page = chats_page.send()
    logger.debug("page: %s", chats_page)
    logger.info("all_messages: %s", chats_page.get_all_messages_once_streaming_has_completed())
    latest_chat_response = chats_page.wait_for_latest_message()
    assert "architecture" in latest_chat_response.text

    # Select files
    chats_page = chats_page.start_new_chat()
    files_to_select = {f.name for f in upload_files if "README" in f.name}
    chats_page.selected_file_names = files_to_select
    chats_page.write_message = "What architecture is in use?"
    chats_page = chats_page.send()

    assert chats_page.selected_file_names == files_to_select
    logger.info("all_messages: %s", chats_page.get_all_messages_once_streaming_has_completed())
    latest_chat_response = chats_page.wait_for_latest_message()
    assert "architecture" in latest_chat_response.text
    assert files_to_select.pop() in latest_chat_response.links

    # Try a file which shouldn't apply to the chat
    chats_page = chats_page.start_new_chat()
    files_to_select = {f.name for f in upload_files if "CODE" in f.name}
    chats_page.selected_file_names = files_to_select
    chats_page.write_message = "What architecture is in use?"
    chats_page = chats_page.send()

    assert chats_page.selected_file_names == files_to_select
    logger.info("all_messages: %s", chats_page.get_all_messages_once_streaming_has_completed())

    # TODO (@brunns): Reinstate assertions once sile selection is affecting the chat response
    # https://technologyprogramme.atlassian.net/browse/REDBOX-337
    # latest_chat_response = chats_page.wait_for_latest_message()
    # assert any(apology in latest_chat_response.text for apology in ["I'm sorry", "I'm afraid"])
    # assert not latest_chat_response.links

    # Delete a file
    documents_page = chats_page.navigate_to_documents()
    pre_delete_doc_count = documents_page.document_count()
    document_delete_page = documents_page.delete_latest_document()
    documents_page = document_delete_page.confirm_deletion()
    assert documents_page.document_count() == pre_delete_doc_count - 1


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
    result = subprocess.run(command, capture_output=True, text=True, check=True)  # noqa: S603
    logger.debug("create_user result: %s", result)


def get_magic_link(email_address: str) -> URL:
    command = ["docker", "compose", "run", "django-app", "venv/bin/django-admin", "show_magiclink_url", email_address]
    result = subprocess.run(command, capture_output=True, text=True, check=True)  # noqa: S603
    magic_link = result.stdout.strip().lstrip("/")
    return BASE_URL / magic_link


@pytest.fixture()
def email_address() -> str:
    username = "".join(choice(string.ascii_lowercase) for _ in range(20))  # noqa: S311
    return f"{username}@cabinetoffice.gov.uk"
