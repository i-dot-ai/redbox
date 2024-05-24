import logging
import os

from playwright.sync_api import Page
from tests_playwright.pages import LandingPage, SignInConfirmationPage

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

email_address = os.environ["USER_EMAIL"]


def test_user_journey(page: Page):
    # Landing page
    landing_page = LandingPage(page)
    sign_in_page = landing_page.navigate_to_sign_in()

    # Sign in
    sign_in_page.email = email_address
    sign_in_page.continue_()

    # Use magic link
    sign_in_confirmation_page = SignInConfirmationPage(page, email_address)
    home_page = sign_in_confirmation_page.navigate_to_home_page()

    # Documents page
    documents_page = home_page.navigate_to_documents()
    document_upload_page = documents_page.navigate_to_upload()

    # Upload a file
    upload_file = document_upload_page.DJANGO_ROOT / "files" / "RiskTriggersReport361.pdf"
    documents_page = document_upload_page.upload_document(upload_file)
    documents_page.assert_contains_file_named(upload_file.name)

    # Chats page
    chats_page = documents_page.navigate_to_chats()
    logger.debug("page: %s", chats_page)
