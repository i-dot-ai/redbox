import logging
import os
import string
import subprocess
from pathlib import Path
from random import choice

import pytest
from pages import LandingPage, SignInConfirmationPage
from playwright.sync_api import Page
from yarl import URL

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

BASE_URL = URL("http://localhost:8090/")
TEST_ROOT = Path(__file__).parent


def test_user_journey(page: Page, email_address: str):
    """End to end user journey test.

    Simulates a single user journey through the application, running against the full suite of microservices.

    Uses the Page Object Model - see https://pinboard.in/u:brunns/t:page-object for some resources explaining this.
    Please add to the page objects in `pages.py` where necessary - don't put page specific logic at this level.

    We should not be asserting anything about AI generated content in this test, aside from asserting that there
    is some."""
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
    chats_page = SignInConfirmationPage.autosubmit(page, magic_link)
    # Dismiss profile overlay
    page.press("body", "Escape")

    # My details page
    my_details_page = chats_page.navigate_my_details()
    my_details_page.name = "Roland Hamilton-Jones"
    my_details_page.ai_experience = "Enthusiastic Experimenter"
    # Add these in once profile overlay is added
    # my_details_page.info_about_user = "Information about user"
    # my_details_page.redbox_response_preferences = "Respond concisely"
    chats_page = my_details_page.update()

    # Documents - keeping stuff which might be useful for later (now we can add documents on the chats page)
    # original_doc_count = documents_page.document_count()
    # upload_files: Sequence[Path] = [f for f in TEST_ROOT.parent.glob("*.md") if f.stat().st_size < 10000]
    # documents_page = document_upload_page.upload_documents(upload_files)
    # document_rows = documents_page.all_documents
    # assert {r.filename for r in document_rows} == {f.name for f in upload_files}
    # assert documents_page.document_count() == original_doc_count + len(upload_files)
    # documents_page.wait_for_documents_to_complete()

    # Chats page
    chats_page = chats_page.start_new_chat()
    chats_page.write_message = "What architecture is in use?"
    chats_page = chats_page.send()
    logger.debug("page: %s", chats_page)
    latest_chat_response = chats_page.wait_for_latest_message()
    assert latest_chat_response.text
    assert "gpt-4o" in chats_page.selected_llm

    # Give user feedback
    chats_page.feedback_stars = 2
    chats_page.improve()
    chats_page.feedback_chips = ["Inaccurate"]
    chats_page.feedback_text = "Could be better."
    chats_page.submit_feedback()

    # Select files
    chats_page = chats_page.start_new_chat()
    # files_to_select = {f.name for f in upload_files if "README" in f.name}
    # chats_page.selected_file_names = files_to_select
    chats_page.write_message = "What licence is in use?"
    chats_page = chats_page.send()
    # assert chats_page.selected_file_names == files_to_select
    latest_chat_response = chats_page.wait_for_latest_message()
    assert latest_chat_response.text

    # Delete a file - keeping stuff which might be useful for later (now we can add documents on the chats page)
    # pre_delete_doc_count = documents_page.document_count()
    # document_delete_page = documents_page.delete_latest_document()
    # documents_page = document_delete_page.confirm_deletion()
    # assert documents_page.document_count() == pre_delete_doc_count - 1

    # Delete a chat
    chats_page = chats_page.start_new_chat()
    pre_chats_count = chats_page.count_chats()
    chats_page.delete_first_chat()
    assert chats_page.count_chats() == pre_chats_count - 1


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
    logger.debug("user created for %s", email_address)


def get_magic_link(email_address: str) -> URL:
    command = ["docker", "compose", "run", "django-app", "venv/bin/django-admin", "show_magiclink_url", email_address]
    result = subprocess.run(command, capture_output=True, text=True, check=True)  # noqa: S603
    magic_link = result.stdout.strip().lstrip("/")
    return BASE_URL / magic_link


@pytest.fixture()
def email_address() -> str:
    username = "".join(choice(string.ascii_lowercase) for _ in range(20))
    return f"{username}@cabinetoffice.gov.uk"
