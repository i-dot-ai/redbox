import os

from playwright.sync_api import Page
from tests_playwright.pages import HomePage

email_address = os.environ["USER_EMAIL"]


def test_has_title(page: Page):
    home_page = HomePage(page)
    sign_in_page = home_page.sign_in()
    sign_in_page.email = email_address
