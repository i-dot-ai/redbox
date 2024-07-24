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
    my_details_page = SignInConfirmationPage.autosubmit(page, magic_link)

    # My details page
    my_details_page.name = "Roland Hamilton-Jones"
    my_details_page.ai_experience = "Enthusiastic Experimenter"
    my_details_page.grade = "AA"
    my_details_page.business_unit = "Delivery Group"
    my_details_page.profession = "Digital, data and technology"
    chats_page = my_details_page.update()

    # Documents page
    documents_page = chats_page.navigate_to_documents()
    original_doc_count = documents_page.document_count()

    # Upload files
    document_upload_page = documents_page.navigate_to_upload()
    upload_files: Sequence[Path] = [f for f in TEST_ROOT.parent.glob("*.md") if f.stat().st_size < 10000]
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
    latest_chat_response = chats_page.wait_for_latest_message()
    assert latest_chat_response.text

    # Give user feedback
    chats_page.feedback_stars = 2
    chats_page.improve()
    chats_page.feedback_chips = ["Inaccurate"]
    chats_page.feedback_text = "Could be better."
    chats_page.submit_feedback()

    # Select files
    chats_page = chats_page.start_new_chat()
    files_to_select = {f.name for f in upload_files if "README" in f.name}
    chats_page.selected_file_names = files_to_select
    chats_page.write_message = "What licence is in use?"
    chats_page = chats_page.send()

    assert chats_page.selected_file_names == files_to_select
    latest_chat_response = chats_page.wait_for_latest_message()
    assert latest_chat_response.text

    # Use specific routes
    for route, select_file, should_have_citation in [
        ("chat", False, False),
        ("chat", True, False),
        ("search", False, True),
        ("search", True, True),
        ("info", False, False),
    ]:
        question = f"@{route} What do I need to install?"
        logger.info("Asking %r", question)
        chats_page.write_message = question
        if select_file:
            files_to_select = {f.name for f in upload_files if "README" in f.name}
            chats_page.selected_file_names = files_to_select
            logger.info("selected %s", files_to_select)
        else:
            chats_page.selected_file_names = []
        chats_page = chats_page.send()
        latest_chat_response = chats_page.wait_for_latest_message()
        assert latest_chat_response.text
        assert latest_chat_response.route.startswith(route)
        if should_have_citation:
            citations_page = latest_chat_response.navigate_to_citations()
            chats_page = citations_page.back_to_chat()
            assert files_to_select.pop() in latest_chat_response.sources
        else:
            assert len(latest_chat_response.sources) == 0

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
